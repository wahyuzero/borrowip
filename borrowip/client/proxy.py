"""Manage pproxy SOCKS5 proxy process."""

import socket
import subprocess
import time


class SocksProxy:
    """Start/stop a local SOCKS5 proxy via pproxy."""

    def __init__(self, port: int = 1080):
        self.port = port
        self._proc = None

    def start(self) -> bool:
        """Start pproxy SOCKS5 server. Raises if it fails."""
        self._proc = subprocess.Popen(
            ["pproxy", "-l", f"socks5://127.0.0.1:{self.port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # Wait for port to be listening
        for _ in range(15):
            time.sleep(0.3)
            try:
                s = socket.socket()
                s.settimeout(1)
                s.connect(("127.0.0.1", self.port))
                s.close()
                return True
            except (ConnectionRefusedError, OSError):
                continue
        raise RuntimeError(f"pproxy failed to start on port {self.port}")

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
