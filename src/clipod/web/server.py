from __future__ import annotations

import http.server
import json
import mimetypes
import shutil
import socketserver
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from clipod.bgm import LayoutError, mix_bgm

WEB_ROOT = Path(__file__).parent
SELECTION_FILE = WEB_ROOT / "selection.json"
BGM_LAYOUT_FILE = WEB_ROOT / "bgm_layout.json"
BGM_DIR = WEB_ROOT / "bgm"
AUTO_FILE: Optional[Path] = None
BACKUP_FILE: Optional[Path] = None


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return  # quiet

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/save":
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length)
            try:
                data = json.loads(payload)
                start = float(data["start"])
                end = float(data["end"])
                file_name = str(data.get("file", ""))
            except Exception:
                self.send_error(400, "Invalid JSON payload")
                return
            SELECTION_FILE.write_text(json.dumps({"start": start, "end": end, "file": file_name}, indent=2))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        if path == "/api/delete":
            if not AUTO_FILE or not AUTO_FILE.exists():
                self.send_error(404, "Auto audio not found")
                return
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length)
            try:
                data = json.loads(payload)
                start = float(data["start"])
                end = float(data["end"])
            except Exception:
                self.send_error(400, "Invalid JSON payload")
                return
            if start < 0 or end <= start:
                self.send_error(400, f"Invalid delete range: start={start}, end={end}")
                return
            backup_path = AUTO_FILE.with_name(f"{AUTO_FILE.stem}_backup{AUTO_FILE.suffix}")
            temp_path = AUTO_FILE.with_name(f"{AUTO_FILE.stem}_tmp{AUTO_FILE.suffix}")
            global BACKUP_FILE
            try:
                shutil.copy2(AUTO_FILE, backup_path)
                BACKUP_FILE = backup_path
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(AUTO_FILE),
                    "-af",
                    f"aselect='not(between(t,{start},{end}))',asetpts=N/SR/TB",
                    str(temp_path),
                ]
                subprocess.run(cmd, check=True)
                temp_path.replace(AUTO_FILE)
            except FileNotFoundError as exc:
                self.send_error(500, "ffmpeg not found. Ensure it is installed and on PATH.")
                return
            except subprocess.CalledProcessError as exc:
                self.send_error(500, f"ffmpeg delete failed with exit code {exc.returncode}")
                return
            finally:
                if temp_path.exists():
                    temp_path.unlink()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        if path == "/api/undo":
            if not AUTO_FILE or not AUTO_FILE.exists():
                self.send_error(404, "Auto audio not found")
                return
            if not BACKUP_FILE or not BACKUP_FILE.exists():
                self.send_error(404, "Backup not found")
                return
            try:
                shutil.copy2(BACKUP_FILE, AUTO_FILE)
            except OSError as exc:
                self.send_error(500, f"Failed to restore backup: {exc}")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        if path == "/api/bgm/upload":
            if not AUTO_FILE or not AUTO_FILE.exists():
                self.send_error(404, "Auto audio not found")
                return
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length)
            name = unquote(self.headers.get("X-File-Name", ""))
            if not name:
                self.send_error(400, "Missing X-File-Name header")
                return
            safe_name = Path(name).name
            if not safe_name:
                self.send_error(400, "Invalid file name")
                return
            BGM_DIR.mkdir(parents=True, exist_ok=True)
            target = BGM_DIR / safe_name
            try:
                target.write_bytes(payload)
            except OSError as exc:
                self.send_error(500, f"Failed to save BGM file: {exc}")
                return
            rel_path = target.relative_to(WEB_ROOT)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "file": str(rel_path)}).encode("utf-8"))
            return
        if path == "/api/bgm/layout":
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length)
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON payload")
                return
            BGM_LAYOUT_FILE.write_text(json.dumps(data, indent=2))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        if path == "/api/mix":
            if not AUTO_FILE or not AUTO_FILE.exists():
                self.send_error(404, "Auto audio not found")
                return
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length)
            try:
                data = json.loads(payload)
                output_name = str(data.get("output", "mixed.wav"))
            except Exception:
                self.send_error(400, "Invalid JSON payload")
                return
            try:
                layout = json.loads(BGM_LAYOUT_FILE.read_text())
            except Exception:
                layout = {"segments": []}
            output_path = AUTO_FILE.with_name(Path(output_name).name)
            def log_command(cmd: list[str]) -> None:
                print("ffmpeg mix command:", " ".join(cmd), flush=True)

            try:
                mix_bgm(
                    main=AUTO_FILE,
                    layout=layout,
                    output=output_path,
                    base_dir=WEB_ROOT,
                    log_command=log_command,
                )
            except LayoutError as exc:
                self.send_error(400, str(exc))
                return
            except FileNotFoundError:
                self.send_error(500, "ffmpeg not found. Ensure it is installed and on PATH.")
                return
            except subprocess.CalledProcessError as exc:
                if exc.stderr:
                    print("ffmpeg mix stderr:\n" + exc.stderr, flush=True)
                self.send_error(500, f"ffmpeg mix failed with exit code {exc.returncode}")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "output": str(output_path)}).encode("utf-8"))
            return
        if path != "/api/save":
            self.send_error(404, "Not Found")
            return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/auto":
            if not AUTO_FILE or not AUTO_FILE.exists():
                self.send_error(404, "Auto audio not found")
                return
            ctype, _ = mimetypes.guess_type(str(AUTO_FILE))
            try:
                data = AUTO_FILE.read_bytes()
            except Exception:
                self.send_error(500, "Failed to read audio file")
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype or "application/octet-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()


def main() -> None:
    port = 8000
    handler = RequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving on http://localhost:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
