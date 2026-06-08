"""SSH reverse tunnel management."""

import os
import signal
import subprocess
import time


class SSHTunnel:
    """Manage an SSH reverse tunnel to a VPS."""

    def __init__(
        self,
        host: str,
        user: str,
        ssh_key: str,
        local_port: int,
        remote_port: int,
        ssh_port: int = 22,
    ):
        self.host = host
        self.user = user
        self.ssh_key = ssh_key
        self.ssh_port = ssh_port
        self.local_port = local_port
        self.remote_port = remote_port
        self._proc = None

    def connect(self):
        """Start SSH reverse tunnel."""
        cmd = [
            "ssh",
            "-i", self.ssh_key,
            "-p", str(self.ssh_port),
            "-R", f"127.0.0.1:{self.remote_port}:127.0.0.1:{self.local_port}",
            "-N",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ExitOnForwardFailure=yes",
            f"{self.user}@{self.host}",
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,  # new process group for clean kill
        )
        # Wait for SSH to establish or fail
        for _ in range(10):
            time.sleep(0.5)
            if self._proc.poll() is not None:
                stderr = self._proc.stderr.read().decode()
                raise RuntimeError(f"SSH tunnel failed: {stderr}")
            # Check if remote port is listening (tunnel ready)
            try:
                import socket
                s = socket.socket()
                s.settimeout(1)
                # Can't directly check remote port from client,
                # just check that SSH is still running after 2s
                s.close()
            except Exception:
                pass
        # Final check
        if self._proc.poll() is not None:
            stderr = self._proc.stderr.read().decode()
            raise RuntimeError(f"SSH tunnel failed: {stderr}")

    def wait(self) -> int:
        """Block until tunnel dies, return exit code."""
        if self._proc:
            return self._proc.wait()
        return -1

    def stop(self):
        """Kill SSH tunnel and all child processes."""
        if self._proc and self._proc.poll() is None:
            try:
                # Kill entire process group
                os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    self._proc.kill()
        self._proc = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
