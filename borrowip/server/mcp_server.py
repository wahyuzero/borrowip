"""BorrowIP MCP Server — exposes proxy tools to AI agents via MCP protocol.

Design principle: Every tool returns plain text that an LLM can directly use.
No ambiguity, no parsing required. If a proxy is available, return its URL.
"""

import json
import socket
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..client.codegen import generate_code
from .fetcher import fetch_via_socks, check_proxy_alive
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
    """Check BorrowIP status. ALWAYS run this first.

    Returns the pair code (for connecting a phone) and lists connected proxies
    with their SOCKS5 ports.

    Example output:
        BorrowIP Status
        Pair code: BIP-ab12cd
        Proxies: 1 connected
          BIP-xw9su6 | socks5://127.0.0.1:10002 | IP: 140.213.141.84 | alive

    If no proxies: tells you the exact Termux command to run.
    """
    pair_code = _get_or_create_pair_code()
    POOL.cleanup_stale()
    clients = POOL.list_all()

    if not clients:
        return (
            f"BorrowIP Status\n"
            f"Pair code: {pair_code}\n"
            f"Proxies: 0 connected\n\n"
            f"No phone connected yet. On your phone (Termux), run:\n"
            f"  borrowip connect {pair_code}@<this-vps-ip>\n\n"
            f"Then ask: 'check borrowip status' again."
        )

    lines = [
        "BorrowIP Status",
        f"Pair code: {pair_code}",
        f"Proxies: {len(clients)} connected",
    ]
    for c in clients:
        age = int(time.time() - c.get("registered_at", time.time()))
        ip = c.get("ip", "unknown")
        alive = "alive" if check_proxy_alive(c["socks_port"]) else "DEAD"
        proxy_url = f"socks5://127.0.0.1:{c['socks_port']}"
        lines.append(
            f"  {c['code']} | {proxy_url} | IP: {ip} | {alive} | {age}s ago"
        )
    return "\n".join(lines)


@mcp.tool()
def borrowip_get_proxy(key: str = "") -> str:
    """Get a ready-to-use SOCKS5 proxy URL.

    Returns the proxy URL string directly (e.g. 'socks5://127.0.0.1:10002').
    Use this URL with any tool that accepts a proxy parameter:
    - CloakBrowser: browser_launch(proxy='socks5://127.0.0.1:10002')
    - curl: curl --socks5-hostname 127.0.0.1:10002 <url>
    - requests: requests.get(url, proxies={'https': 'socks5h://127.0.0.1:10002'})

    Args:
        key: Optional connection code (e.g. BIP-xxxxxx). If omitted, uses first available.
    """
    client = POOL.get(key) if key else POOL.get_any()
    if not client:
        pair_code = _get_or_create_pair_code()
        return (
            f"ERROR: No proxy connected. "
            f"Run on Termux: borrowip connect {pair_code}@<vps-ip>"
        )

    if not check_proxy_alive(client["socks_port"]):
        return (
            f"ERROR: Proxy {client['code']} on port {client['socks_port']} is not responding. "
            f"The SSH tunnel may have dropped. Ask user to reconnect from Termux."
        )

    proxy_url = f"socks5://127.0.0.1:{client['socks_port']}"
    ip = client.get("ip", "unknown")
    return f"{proxy_url} | code={client['code']} | IP={ip}"


@mcp.tool()
def borrowip_fetch(url: str, key: str = "") -> str:
    """Fetch a URL through the mobile proxy.

    Use when a website blocks your server/VPS IP (Cloudflare, rate limits, geo-blocks).
    The request goes through the phone's cellular connection instead.

    Args:
        url: The URL to fetch
        key: Optional connection code. If omitted, uses first available proxy.
    """
    client = POOL.get(key) if key else POOL.get_any()
    if not client:
        pair_code = _get_or_create_pair_code()
        return (
            f"ERROR: No proxy available. "
            f"Run on Termux: borrowip connect {pair_code}@<this-vps-ip>"
        )

    try:
        body = fetch_via_socks(client["socks_port"], url)
        if len(body) > 500_000:
            body = body[:500_000] + f"\n\n... truncated ({len(body)} bytes total)"
        return body
    except Exception as e:
        return (
            f"ERROR: Fetch failed via port {client['socks_port']}: {e}\n"
            f"The tunnel may have dropped. Ask user to reconnect from Termux."
        )


@mcp.tool()
def borrowip_check_ip(key: str = "") -> str:
    """Check the external IP address of the mobile proxy.

    Useful to verify the proxy is working and see which IP/cellular network is being used.

    Args:
        key: Optional connection code. If omitted, uses first available proxy.
    """
    client = POOL.get(key) if key else POOL.get_any()
    if not client:
        return "ERROR: No proxy available. Connect your phone first."

    try:
        ip = None
        for check_url in [
            "https://api.ipify.org",
            "https://api64.ipify.org",
            "https://icanhazip.com",
            "http://httpbin.org/ip",
        ]:
            try:
                body = fetch_via_socks(client["socks_port"], check_url, timeout=15)
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
            return "ERROR: Could not determine proxy IP (all check services failed)"

        try:
            client["ip"] = ip
            (DATA_DIR / "clients" / f"{client['code']}.json").write_text(
                json.dumps(client)
            )
        except OSError:
            pass
        return f"Proxy IP: {ip}"
    except Exception as e:
        return f"ERROR: Check failed: {e}"


@mcp.tool()
def borrowip_list_proxies() -> str:
    """List all connected mobile proxies with details.

    Returns one line per proxy: code, SOCKS5 URL, IP, age, alive status.
    """
    clients = POOL.list_all()
    if not clients:
        return "No proxies connected."
    lines = []
    for c in clients:
        proxy_url = f"socks5://127.0.0.1:{c['socks_port']}"
        alive = "alive" if check_proxy_alive(c["socks_port"]) else "DEAD"
        age = int(time.time() - c.get("registered_at", time.time()))
        ip = c.get("ip", "unknown")
        lines.append(f"{c['code']} | {proxy_url} | IP: {ip} | {alive} | {age}s ago")
    return "\n".join(lines)


@mcp.tool()
def borrowip_health_check(key: str = "") -> str:
    """Quick liveness check — is the proxy tunnel actually working?

    Tests if the SOCKS5 port is open AND can reach the internet.
    Much faster than borrowip_fetch (3s timeout vs 30s).

    Args:
        key: Optional connection code. If omitted, checks first available proxy.
    """
    client = POOL.get(key) if key else POOL.get_any()
    if not client:
        return "ERROR: No proxy connected."

    port = client["socks_port"]

    # Step 1: Is the port even open?
    if not check_proxy_alive(port):
        return (
            f"DEAD: Port {port} not responding. "
            f"Tunnel dropped. Ask user to reconnect from Termux."
        )

    # Step 2: Can it actually reach the internet?
    try:
        body = fetch_via_socks(port, "https://api.ipify.org", timeout=5)
        ip = body.strip() if body else "unknown"
        return f"ALIVE: Port {port} working. External IP: {ip}"
    except Exception:
        return (
            f"STALE: Port {port} is open but cannot reach internet. "
            f"Tunnel may be dying. Ask user to reconnect from Termux."
        )


def main():
    """Entry point for borrowip-mcp command."""
    pair_code = _get_or_create_pair_code()

    POOL.cleanup_stale()

    print(f"BorrowIP MCP Server", file=sys.stderr)
    print(f"Pair code: {pair_code}", file=sys.stderr)
    print(f"Run on Termux: borrowip connect {pair_code}@<this-vps-ip>", file=sys.stderr)
    print(f"Data dir: {DATA_DIR}", file=sys.stderr)

    mcp.run()
