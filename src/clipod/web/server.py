from __future__ import annotations

import http.server
import json
import mimetypes
import os
import shutil
import socketserver
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from clipod.bgm import LayoutError, mix_bgm


def _parse_multipart_form(content_type: str, payload: bytes) -> tuple[str, bytes]:
    if "boundary=" not in content_type:
        raise ValueError("Missing multipart boundary")
    boundary = content_type.split("boundary=", 1)[1]
    boundary_bytes = ("--" + boundary).encode("utf-8")
    parts = payload.split(boundary_bytes)
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        header, _, body = part.partition(b"\r\n\r\n")
        if b'name="file"' not in header:
            continue
        filename = "upload.wav"
        for segment in header.split(b";"):
            segment = segment.strip()
            if segment.startswith(b"filename="):
                raw = segment.split(b"=", 1)[1].strip().strip(b'"')
                if raw:
                    filename = raw.decode("utf-8", errors="replace")
        body = body.rstrip(b"\r\n")
        return filename, body
    raise ValueError("No file field found")

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
        if path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self.send_error(400, "Expected multipart/form-data")
                return
            if not AUTO_FILE:
                self.send_error(500, "Auto file path not configured")
                return
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length)
            try:
                filename, data = _parse_multipart_form(content_type, payload)
            except ValueError as exc:
                self.send_error(400, str(exc))
                return
            AUTO_FILE.parent.mkdir(parents=True, exist_ok=True)
            try:
                AUTO_FILE.write_bytes(data)
            except OSError as exc:
                self.send_error(500, f"Failed to save upload: {exc}")
                return
            os.sync()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "file": filename}).encode("utf-8"))
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
                print(f"BEFORE DELETE: {AUTO_FILE.stat().st_size} bytes", flush=True)
                filter_complex = (
                    f"[0:a]atrim=0:{start},asetpts=PTS-STARTPTS[a];"
                    f"[0:a]atrim={end},asetpts=PTS-STARTPTS[b];"
                    "[a][b]concat=n=2:v=0:a=1[out]"
                )
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(AUTO_FILE),
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[out]",
                    str(temp_path),
                ]
                print(f"DELETE MAIN: {AUTO_FILE}", flush=True)
                print(f"DELETE TMP: {temp_path}", flush=True)
                print(f"FFMPEG CMD: {' '.join(cmd)}", flush=True)
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(f"DELETE RETURN CODE: {result.returncode}", flush=True)
                if result.stderr:
                    print(f"DELETE STDERR: {result.stderr}", flush=True)
                if temp_path.exists():
                    print(f"TMP FILE SIZE: {temp_path.stat().st_size} bytes", flush=True)
                print(f"REPLACE BEFORE: {AUTO_FILE.exists()} -> {temp_path.exists()}", flush=True)
                temp_path.replace(AUTO_FILE)
                print(f"REPLACE AFTER: {AUTO_FILE.exists()} -> {temp_path.exists()}", flush=True)
                print(f"DELETE REPLACED: {AUTO_FILE.exists()}", flush=True)
                print(f"AFTER DELETE: {AUTO_FILE.stat().st_size} bytes", flush=True)
                os.sync()
                try:
                    with open(AUTO_FILE, "rb") as handle:
                        os.fsync(handle.fileno())
                except OSError:
                    pass
                os.sync()
            except FileNotFoundError as exc:
                self.send_error(500, "ffmpeg not found. Ensure it is installed and on PATH.")
                return
            except subprocess.CalledProcessError as exc:
                if exc.stderr:
                    print(f"DELETE STDERR: {exc.stderr}", flush=True)
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
                AUTO_FILE.touch()
                with open(AUTO_FILE, "rb", buffering=0) as handle:
                    data = handle.read()
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
