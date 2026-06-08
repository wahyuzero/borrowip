"""Fetch URL through SOCKS5 proxy."""

import requests


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
            # Return error body for non-2xx but with status info
            return f"HTTP {e.response.status_code}: {e.response.text}"
        except Exception as e:
            errors.append(f"{host}: {e}")
            continue

    raise ConnectionError(
        f"No SOCKS proxy found on port {socks_port}. "
        f"Tried: {'; '.join(errors)}"
    )
