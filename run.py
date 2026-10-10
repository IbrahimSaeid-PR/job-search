from __future__ import annotations

import socket
import sys
import threading
import time

import uvicorn
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import settings
from app.main import app
from app.ui.main_window import MainWindow


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def start_backend() -> uvicorn.Server:
    config = uvicorn.Config(
        app, host=settings.backend_host, port=settings.backend_port, log_level="warning"
    )
    server = uvicorn.Server(config)
    # uvicorn must not install signal handlers from a non-main thread.
    server.install_signal_handlers = lambda: None
    threading.Thread(target=server.run, daemon=True, name="jobfinder-backend").start()
    return server


def wait_until_ready(server: uvicorn.Server, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.started:
            return True
        time.sleep(0.05)
    return False


def main() -> int:
    qt_app = QApplication(sys.argv)
    if _port_in_use(settings.backend_host, settings.backend_port):
        QMessageBox.critical(
            None,
            "JobFinder",
            f"Port {settings.backend_port} is already in use.\n"
            "Close the other JobFinder window or change BACKEND_PORT in .env.",
        )
        return 1
    server = start_backend()
    if not wait_until_ready(server):
        QMessageBox.critical(None, "JobFinder", "The local search service failed to start.")
        server.should_exit = True
        return 1
    window = MainWindow()
    window.show()
    code = qt_app.exec()
    server.should_exit = True
    return code


if __name__ == "__main__":
    sys.exit(main())
