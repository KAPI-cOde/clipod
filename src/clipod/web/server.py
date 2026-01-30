from __future__ import annotations

import http.server
import json
import mimetypes
import socketserver
from pathlib import Path
from typing import Optional

WEB_ROOT = Path(__file__).parent
SELECTION_FILE = WEB_ROOT / "selection.json"
AUTO_FILE: Optional[Path] = None


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return  # quiet

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/save":
            self.send_error(404, "Not Found")
            return
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

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/auto":
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
