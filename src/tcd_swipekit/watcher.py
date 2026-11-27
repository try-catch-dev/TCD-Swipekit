"""Live watch & hot-reload preview server for TCD-Swipekit (`swipekit watch`)."""

from __future__ import annotations

import functools
import json
import threading
import time
from collections.abc import Callable
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def collect_watched_files(target_file: Path, extra_files: list[Path] | None = None) -> list[Path]:
    """Collect the target deck/markdown file and any referenced custom theme files."""
    files: list[Path] = [target_file.resolve()]
    if extra_files:
        for f in extra_files:
            if f and f.is_file():
                resolved = f.resolve()
                if resolved not in files:
                    files.append(resolved)
    return files


def snapshot_mtimes(files: list[Path]) -> dict[Path, int]:
    """Return a mapping of file paths to their modification time in nanoseconds."""
    state: dict[Path, int] = {}
    for p in files:
        if p.is_file():
            state[p] = p.stat().st_mtime_ns
    return state


class _SwipekitPreviewHandler(SimpleHTTPRequestHandler):
    """Serves `output_dir` with `/__swipekit_version` JSON endpoint for live browser reload."""

    def __init__(
        self,
        *args: object,
        directory: str,
        get_version: Callable[[], int],
        **kwargs: object,
    ) -> None:
        self._get_version = get_version
        super().__init__(*args, directory=directory, **kwargs)  # type: ignore[arg-type]

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/__swipekit_version"):
            payload = json.dumps({"version": self._get_version()}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path in ("/", "/index.html"):
            self.path = "/preview.html"
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Keep terminal clean during watch mode
        return


def run_watch_server(
    *,
    target_file: Path,
    output_dir: Path,
    render_callback: Callable[[], None],
    extra_watch_files: list[Path] | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    poll_interval: float = 0.75,
    on_rebuild: Callable[[int, Path], None] | None = None,
    serve_http: bool = True,
    max_cycles: int | None = None,
) -> int:
    """Render once, optionally serve `output_dir` over HTTP, and re-render on file changes.

    Returns the total number of renders executed.
    """
    build_version = 1
    render_callback()

    watched = collect_watched_files(target_file, extra_watch_files)
    last_mtimes = snapshot_mtimes(watched)

    server: ThreadingHTTPServer | None = None
    if serve_http:
        handler_cls = functools.partial(
            _SwipekitPreviewHandler,
            directory=str(output_dir.resolve()),
            get_version=lambda: build_version,
        )
        server = ThreadingHTTPServer((host, port), handler_cls)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

    cycles = 0
    try:
        while True:
            if max_cycles is not None and cycles >= max_cycles:
                break
            time.sleep(poll_interval)
            cycles += 1
            current_mtimes = snapshot_mtimes(watched)
            changed_path: Path | None = None
            for path, mtime in current_mtimes.items():
                if last_mtimes.get(path) != mtime:
                    changed_path = path
                    break
            if changed_path is not None:
                last_mtimes = current_mtimes
                render_callback()
                build_version += 1
                if on_rebuild is not None:
                    on_rebuild(build_version, changed_path)
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()

    return build_version
