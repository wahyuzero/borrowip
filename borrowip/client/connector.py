"""Main client connector — orchestrates proxy + tunnel + registration."""

import json
import os
import re
import signal
import subprocess
import sys
import time

from .codegen import generate_code
from .proxy import SocksProxy
from .tunnel import SSHTunnel

# Valid pair code: BIP-xxxxxx (6 alphanumeric chars)
CODE_RE = re.compile(r'^BIP-[a-z0-9]{6}$')


def _validate_code(code: str) -> str:
    """Validate pair code format to prevent shell injection."""
    if not CODE_RE.match(code):
        raise ValueError(
            f"Invalid code format: {code!r}. "
            "Expected format: BIP-xxxxxx (6 alphanumeric chars)"
        )
    return code


def connect(
    host: str,
    code: str = "",
    ssh_user: str = "root",
    ssh_key: str = "",
    ssh_port: int = 22,
    local_port: int = 1080,
    remote_port: int = 0,
):
    """
    Connect to VPS and borrow mobile IP.

    Args:
        host: VPS IP or hostname
        code: Pair code from VPS (auto-generated if empty)
        ssh_user: SSH username
        ssh_key: Path to SSH key
        ssh_port: SSH port
        local_port: Local SOCKS proxy port
        remote_port: Remote port (0 = auto-detect from VPS)
    """
    if not code:
        code = generate_code()
    _validate_code(code)

    if not ssh_key:
        ssh_key = _find_ssh_key()
        if not ssh_key:
            print("❌ No SSH key found. Use --key or run: ssh-keygen")
            sys.exit(1)

    # Auto-detect remote port from VPS if not specified
    if remote_port == 0:
        remote_port = _find_free_remote_port(host, ssh_user, ssh_key, ssh_port)

    print(f"🔗 BorrowIP — Connecting to {host}")
    print(f"   Code: {code}")
    print(f"   SSH: {ssh_user}@{host}:{ssh_port}")
    print(f"   SOCKS: local:{local_port} → remote:{remote_port}")

    # Start local SOCKS proxy
    proxy = SocksProxy(local_port)
    try:
        proxy.start()
        print(f"✅ SOCKS5 proxy on :{local_port}")
    except Exception as e:
        print(f"❌ Failed to start SOCKS proxy: {e}")
        print(f"   Install pproxy: pip install pproxy")
        sys.exit(1)

    # SSH tunnel with auto-reconnect
    tunnel = SSHTunnel(
        host=host,
        user=ssh_user,
        ssh_key=ssh_key,
        ssh_port=ssh_port,
        local_port=local_port,
        remote_port=remote_port,
    )

    while True:
        try:
            tunnel.stop()  # cleanup any previous process
            tunnel.connect()
            print("✅ SSH tunnel established!")

            # Register on VPS
            _register_on_vps(host, ssh_user, ssh_key, ssh_port, code, remote_port)
            print(f"✅ Registered: {code}")
            print()
            print("=" * 44)
            print(f"  📡 BorrowIP Connected!")
            print(f"  Code: {code}")
            print(f"  Tell AI: 'use borrowip key {code}'")
            print("=" * 44)
            print()

            # Block until tunnel dies
            exit_code = tunnel.wait()
            print(f"⚠️  Tunnel disconnected (exit: {exit_code})")

        except KeyboardInterrupt:
            print("\n👋 Disconnecting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

        print("🔄 Reconnecting in 5s... (Ctrl+C to stop)")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            break

    # Cleanup
    tunnel.stop()
    proxy.stop()
    print("👋 Disconnected.")


def _find_ssh_key() -> str:
    """Find SSH key in common locations."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".ssh", "id_ed25519"),
        os.path.join(home, ".ssh", "id_rsa"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _find_free_remote_port(host, user, key, ssh_port) -> int:
    """Query VPS for next available remote port."""
    # Default range: 10001-10010
    remote_cmd = (
        "python3 -c \""
        "from pathlib import Path;"
        "import json;"
        "d=Path('/tmp/.borrowip/clients');"
        "used=set();"
        "[used.add(json.loads(f.read_text()).get('socks_port',0)) "
        "for f in d.glob('*.json')] if d.exists() else None;"
        "p=10001;"
        "[print(p) if p not in used else None "
        "for p in range(10001,10011)]"
        "\" 2>/dev/null | head -1"
    )
    # Fallback: just use ss to find used ports
    remote_cmd = (
        "ports=$(ss -tlnp 2>/dev/null | grep -oP '127.0.0.1:\\K[0-9]+' | sort -un); "
        "for p in $(seq 10001 10010); do "
        "echo $ports | grep -qw $p || { echo $p; break; }; "
        "done"
    )
    cmd = [
        "ssh", "-i", key, "-p", str(ssh_port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{user}@{host}",
        remote_cmd,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except Exception:
        pass
    return 10001  # fallback


def _register_on_vps(host, user, key, ssh_port, code, remote_port):
    """Write registration file on VPS via SSH."""
    # Validate code to prevent shell injection
    _validate_code(code)

    payload = json.dumps({
        "code": code,
        "socks_port": remote_port,
        "registered_at": int(time.time()),
    })
    remote_cmd = (
        f"mkdir -p /tmp/.borrowip/clients && "
        f"cat > /tmp/.borrowip/clients/{code}.json << 'BIPJSON'\n"
        f"{payload}\n"
        f"BIPJSON"
    )
    cmd = [
        "ssh",
        "-i", key,
        "-p", str(ssh_port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{user}@{host}",
        remote_cmd,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"Registration failed: {result.stderr.strip()}")
