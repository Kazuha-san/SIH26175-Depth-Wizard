"""
Desktop launcher -- runs DepthWizard as one native-window application on
this machine. No browser tab, no separate frontend dev server: this starts
the FastAPI backend in the background and opens the built frontend
(frontend/dist/, see main.py's static mount) in a real OS window via
pywebview.

ONE-TIME SETUP (build the frontend once, or after any frontend change):
    cd frontend
    npm install
    npm run build

RUN THE APP:
    cd backend
    python desktop_app.py

This is the intended way to run DepthWizard day to day. `uvicorn
app.main:app --reload` (see main.py) is still there for API-only backend
development, and `npm run dev` (port 5173) is still there for frontend-only
development with hot reload -- neither of those opens a native window,
they're dev tools, not the app itself.
"""
import socket
import threading
import time

import uvicorn
import webview

HOST = "127.0.0.1"
PORT = 8000


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def _run_server():
    from app.main import app

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_for_server(timeout_s: float = 20.0):
    """Blocks until uvicorn is actually accepting connections, rather than
    guessing with a fixed sleep -- a fixed sleep is either too short (window
    opens to a connection-refused blank page) or wastefully too long on a
    fast machine."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _port_is_open(HOST, PORT):
            return
        time.sleep(0.1)
    raise RuntimeError(
        f"Backend didn't come up on {HOST}:{PORT} within {timeout_s}s -- "
        f"check the terminal for a startup error (e.g. missing model "
        f"checkpoint, missing dependency)."
    )


def main():
    from pathlib import Path

    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if not frontend_dist.is_dir():
        raise SystemExit(
            "frontend/dist/ not found -- build the frontend first:\n"
            "    cd frontend && npm install && npm run build\n"
            "then re-run this script."
        )

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    _wait_for_server()

    webview.create_window(
        "DepthWizard",
        f"http://{HOST}:{PORT}",
        width=1440,
        height=900,
        min_size=(1024, 700),
    )
    webview.start()


if __name__ == "__main__":
    main()
