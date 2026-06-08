"""Proxy pool — manages connected proxy clients via filesystem."""

import json
import time
from pathlib import Path


class ProxyPool:
    """Read proxy client registrations from /tmp/.borrowip/clients/."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.clients_dir = data_dir / "clients"
        self.clients_dir.mkdir(parents=True, exist_ok=True)

    def register(self, code: str, socks_port: int) -> dict:
        """Register a new client (usually called by the client via SSH)."""
        client = {
            "code": code,
            "socks_port": socks_port,
            "registered_at": int(time.time()),
            "ip": "",
        }
        (self.clients_dir / f"{code}.json").write_text(json.dumps(client))
        return client

    def unregister(self, code: str):
        """Remove a client registration."""
        f = self.clients_dir / f"{code}.json"
        if f.exists():
            f.unlink()

    def get(self, code: str) -> dict | None:
        """Get a specific client by code."""
        if not code:
            return self.get_any()
        f = self.clients_dir / f"{code}.json"
        if f.exists():
            return json.loads(f.read_text())
        return None

    def get_any(self) -> dict | None:
        """Get any available client (first found)."""
        clients = self.list_all()
        return clients[0] if clients else None

    def list_all(self) -> list[dict]:
        """List all registered clients."""
        result = []
        for f in sorted(self.clients_dir.glob("BIP-*.json")):
            try:
                result.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
        return result

    def cleanup_stale(self, max_age_seconds: int = 86400):
        """Remove registrations older than max_age_seconds."""
        now = time.time()
        for f in self.clients_dir.glob("BIP-*.json"):
            try:
                client = json.loads(f.read_text())
                if now - client.get("registered_at", 0) > max_age_seconds:
                    f.unlink()
            except (json.JSONDecodeError, OSError):
                f.unlink(missing_ok=True)
