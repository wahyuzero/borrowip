"""BorrowIP CLI entry point."""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="borrowip",
        description="Borrow mobile IP for AI agents via SSH reverse tunnel",
    )
    subparsers = parser.add_subparsers(dest="command")

    # connect
    p_connect = subparsers.add_parser("connect", help="Connect to VPS from Termux")
    p_connect.add_argument("target", nargs="?", help="Code@host or just host")
    p_connect.add_argument("--code", "-c", default="", help="Pair code")
    p_connect.add_argument("--host", help="VPS hostname/IP")
    p_connect.add_argument("--user", "-u", default="", help="SSH user")
    p_connect.add_argument("--key", "-i", default="", help="SSH key path (override config)")
    p_connect.add_argument("--port", "-p", type=int, default=22, help="SSH port")
    p_connect.add_argument(
        "--local-port", type=int, default=1080, help="Local SOCKS port"
    )
    p_connect.add_argument(
        "--remote-port", type=int, default=0, help="Remote SOCKS port (0=auto)"
    )

    # init
    subparsers.add_parser("init", help="Setup config file")

    # status
    subparsers.add_parser("status", help="Check local connection status")

    # pair-code
    subparsers.add_parser("pair-code", help="Show current pair code")

    args = parser.parse_args()

    if args.command == "connect":
        _handle_connect(args)
    elif args.command == "init":
        _handle_init()
    elif args.command == "status":
        _handle_status()
    elif args.command == "pair-code":
        _handle_pair_code()
    else:
        parser.print_help()


def _load_config() -> dict:
    """Load config from ~/.borrowip.toml if it exists."""
    config_path = os.path.expanduser("~/.borrowip.toml")
    if not os.path.exists(config_path):
        return {}

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def _handle_connect(args):
    from borrowip.client.connector import connect

    code = args.code
    host = args.host or ""
    user = args.user
    ssh_key = args.key
    ssh_password = ""

    # Parse target: BIP-xxxx@host or just host
    if args.target:
        if "@" in args.target:
            parts = args.target.split("@", 1)
            code = code or parts[0]
            host = host or parts[1]
        else:
            host = host or args.target

    # Fall back to config file
    config = _load_config()
    server = config.get("server", {})
    host = host or server.get("host", "")
    user = user or server.get("user", "root")
    ssh_key = ssh_key or server.get("ssh_key", "")
    ssh_password = server.get("ssh_password", "")

    if not host:
        print("❌ No host specified.")
        print("   Usage: borrowip connect BIP-xxxx@host")
        print("   Or run: borrowip init")
        sys.exit(1)

    if not user:
        print("❌ No SSH user specified. Run: borrowip init")
        sys.exit(1)

    if not ssh_key and not ssh_password:
        print("❌ No SSH key or password configured. Run: borrowip init")
        sys.exit(1)

    connect(
        host=host,
        code=code,
        ssh_user=user,
        ssh_key=ssh_key,
        ssh_password=ssh_password,
        ssh_port=args.port,
        local_port=args.local_port,
        remote_port=args.remote_port,
    )


def _handle_init():
    print("🔧 BorrowIP Setup\n")
    host = input("VPS IP/hostname: ").strip()
    user = input("SSH user [root]: ").strip() or "root"
    auth_method = input("Auth method: (k)ey / (p)assword [k]: ").strip().lower()

    config_lines = [f"[server]", f'host = "{host}"', f'user = "{user}"']

    if auth_method == "p":
        password = input("SSH password: ").strip()
        config_lines.append(f'ssh_password = "{password}"')
    else:
        key = input("SSH key path [~/.ssh/id_ed25519]: ").strip() or "~/.ssh/id_ed25519"
        config_lines.append(f'ssh_key = "{key}"')

    config = "\n".join(config_lines) + "\n"

    path = os.path.expanduser("~/.borrowip.toml")
    with open(path, "w") as f:
        f.write(config)
    print(f"\n✅ Config saved to {path}")
    print(f"Run: borrowip connect")


def _handle_status():
    clients_dir = Path("/tmp/.borrowip/clients")
    if clients_dir.exists():
        clients = list(clients_dir.glob("BIP-*.json"))
        if clients:
            print("📡 Connected proxies:")
            for f in clients:
                try:
                    c = json.loads(f.read_text())
                    print(f"  • {c['code']} → socks5 :{c['socks_port']}")
                except (json.JSONDecodeError, OSError):
                    pass
        else:
            print("No active connections.")
    else:
        print("No active connections.")

    pair_file = Path("/tmp/.borrowip/pair-code.txt")
    if pair_file.exists():
        print(f"\nPair code: {pair_file.read_text().strip()}")


def _handle_pair_code():
    pair_file = Path("/tmp/.borrowip/pair-code.txt")
    if pair_file.exists():
        print(pair_file.read_text().strip())
    else:
        from borrowip.client.codegen import generate_code

        code = generate_code()
        pair_file.parent.mkdir(parents=True, exist_ok=True)
        pair_file.write_text(code)
        print(code)


if __name__ == "__main__":
    main()
