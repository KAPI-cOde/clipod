from __future__ import annotations

import contextlib
import threading
import webbrowser
from pathlib import Path

import click

from clipod.web import server as web_server


@click.command(name="web")
@click.argument("audio_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--port", "-p", type=int, default=8000, show_default=True, help="Port to serve the editor on.")
@click.option("--open/--no-open", "open_browser", default=True, show_default=True, help="Open browser automatically.")
def web_command(audio_file: Path, port: int, open_browser: bool) -> None:
    """Launch the waveform editor web UI."""
    from http.server import HTTPServer

    # stash path so server can serve it via /api/auto
    web_server.AUTO_FILE = audio_file

    handler = web_server.RequestHandler
    server = HTTPServer(("", port), handler)

    def serve() -> None:
        with contextlib.suppress(Exception):
            server.serve_forever()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    url = f"http://localhost:{port}/?file=auto"
    click.echo(f"Serving waveform editor at {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        thread.join()
    except KeyboardInterrupt:
        click.echo("Shutting down...")
        server.shutdown()
