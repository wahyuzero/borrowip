"""Fetch URL through SOCKS5 proxy and check proxy liveness."""

import socket

import requests


def check_proxy_alive(socks_port: int, timeout: float = 3.0) -> bool:
    """Quick TCP check — is the SOCKS5 port open and accepting connections?

    This is NOT a full proxy test. It just checks if something is listening.
    Use fetch_via_socks() for a real end-to-end test.
    """
    if not (0 < socks_port <= 65535):
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(("127.0.0.1", socks_port))
            return True
    except (socket.timeout, ConnectionRefusedError, OSError, OverflowError, ValueError):
        return False


def fetch_via_socks(socks_port: int, url: str, timeout: int = 30, verify_ssl: bool = False) -> str:
    """
    Fetch a URL through a local SOCKS5 proxy.

    Tries IPv4 first, then IPv6 loopback.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    }

    errors = []
    for host in ["127.0.0.1", "::1"]:
        proxy = f"socks5h://{host}:{socks_port}"
        proxies = {"http": proxy, "https": proxy}
        try:
            r = requests.get(
                url,
                proxies=proxies,
                timeout=timeout,
                headers=headers,
                verify=verify_ssl,
            )
            r.raise_for_status()
            return r.text
        except requests.exceptions.HTTPError as e:
            return f"HTTP {e.response.status_code}: {e.response.text}"
        except Exception as e:
            errors.append(f"{host}: {e}")
            continue

    raise ConnectionError(
        f"No SOCKS proxy found on port {socks_port}. "
        f"Tried: {'; '.join(errors)}"
    )
