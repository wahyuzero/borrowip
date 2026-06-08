"""BorrowIP MCP Server — exposes proxy tools to AI agents via MCP protocol."""

import json
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..client.codegen import generate_code
from .fetcher import fetch_via_socks
from .proxy_pool import ProxyPool

# Data directory
DATA_DIR = Path("/tmp/.borrowip")
DATA_DIR.mkdir(parents=True, exist_ok=True)

POOL = ProxyPool(DATA_DIR)
mcp = FastMCP("borrowip")


def _get_or_create_pair_code() -> str:
    """Get or create a pair code for this VPS."""
    pair_file = DATA_DIR / "pair-code.txt"
    if pair_file.exists():
        return pair_file.read_text().strip()
    code = generate_code()
    pair_file.write_text(code)
    return code


@mcp.tool()
def borrowip_status() -> str:
    """Check BorrowIP status — shows pair code and connected mobile proxies.

    Run this first to get your pair code for connecting Termux.
    """
    pair_code = _get_or_create_pair_code()
    POOL.cleanup_stale()
    clients = POOL.list_all()

    if not clients:
        return (
            f"📡 BorrowIP Status\n"
            f"Pair code: {pair_code}\n"
            f"Connected proxies: none\n\n"
            f"On your phone (Termux), run:\n"
            f"  borrowip connect {pair_code}@<this-vps-ip>"
        )

    lines = [
        "📡 BorrowIP Status",
        f"Pair code: {pair_code}",
        f"Connected proxies ({len(clients)}):",
    ]
    for c in clients:
        age = int(time.time() - c.get("registered_at", time.time()))
        ip = c.get("ip", "?")
        lines.append(f"  • {c['code']} → socks5 :{c['socks_port']} (IP: {ip}, {age}s ago)")
    return "\n".join(lines)


@mcp.tool()
def borrowip_fetch(url: str, key: str = "") -> str:
    """Fetch a URL through mobile proxy. Use when target site blocks server/VPS IP.

    Args:
        url: The URL to fetch
        key: Connection code from borrowip_status (e.g. BIP-xxxxxx). Optional if only one proxy connected.
    """
    client = POOL.get(key) if key else POOL.get_any()
    if not client:
        pair_code = _get_or_create_pair_code()
        return (
            f"❌ No proxy available.\n"
            f"Run on Termux: borrowip connect {pair_code}@<this-vps-ip>"
        )

    try:
        body = fetch_via_socks(client["socks_port"], url)
        # Truncate huge responses
        if len(body) > 500_000:
            body = body[:500_000] + f"\n\n... truncated ({len(body)} bytes total)"
        return body
    except Exception as e:
        return f"❌ Fetch failed via :{client['socks_port']}: {e}"


@mcp.tool()
def borrowip_check_ip(key: str = "") -> str:
    """Check which IP address the mobile proxy is using.

    Args:
        key: Connection code. Optional if only one proxy connected.
    """
    client = POOL.get(key) if key else POOL.get_any()
    if not client:
        return "❌ No proxy available. Connect your phone first."

    try:
        # Try multiple IP check services as fallback
        ip = None
        for check_url in [
            "https://api.ipify.org",
            "https://api64.ipify.org",
            "https://icanhazip.com",
            "http://httpbin.org/ip",
        ]:
            try:
                body = fetch_via_socks(client["socks_port"], check_url, timeout=15)
                # Parse response
                try:
                    ip_data = json.loads(body)
                    ip = ip_data.get("origin", body.strip())
                except (json.JSONDecodeError, KeyError):
                    ip = body.strip()
                if ip:
                    break
            except Exception:
                continue

        if not ip:
            return "❌ Could not determine proxy IP (all check services failed)"

        # Update stored IP
        try:
            client["ip"] = ip
            (DATA_DIR / "clients" / f"{client['code']}.json").write_text(
                json.dumps(client)
            )
        except OSError:
            pass
        return f"✅ Proxy IP: {ip}"
    except Exception as e:
        return f"❌ Check failed: {e}"


@mcp.tool()
def borrowip_list_proxies() -> str:
    """List all connected mobile proxies with their details."""
    clients = POOL.list_all()
    if not clients:
        return "No proxies connected."
    lines = []
    for c in clients:
        lines.append(
            f"• {c['code']} | port :{c['socks_port']} | IP: {c.get('ip', 'unknown')}"
        )
    return "\n".join(lines)


def main():
    """Entry point for borrowip-mcp command."""
    pair_code = _get_or_create_pair_code()

    # Clean up stale registrations from previous sessions
    POOL.cleanup_stale()

    print(f"📡 BorrowIP MCP Server", file=sys.stderr)
    print(f"Pair code: {pair_code}", file=sys.stderr)
    print(f"Run on Termux: borrowip connect {pair_code}@<this-vps-ip>", file=sys.stderr)
    print(f"Data dir: {DATA_DIR}", file=sys.stderr)

    mcp.run()
