# BorrowIP 📡

**Borrow mobile IP for AI agents** — route traffic through your phone's cellular connection via SSH reverse tunnel.

Zero infrastructure. Uses existing SSH (port 22). Works with any MCP-compatible AI agent.

## How it works

```
📱 Phone (Termux)           🖥️ VPS                   🤖 AI Agent
────────────────            ─────────                ──────────
borrowip connect            borrowip-mcp             Hermes/Claude
  BIP-xxxx@vps-ip             (auto-started)             ↓
    │                             │                  borrowip_fetch()
    ├── SSH :22 ──────────────→  SSH :22                ↓
    │  pproxy :1080              SOCKS5 :10001       → cellular IP
    └── cellular ──→ internet ←──┘
```

## Quick Start

### 1. VPS: Install & configure AI agent

```bash
git clone https://github.com/wahyuzero/borrowip
cd borrowip && pip install -e .
```

Add to your AI agent config (e.g. Hermes `config.yaml`):

```yaml
mcp_servers:
  borrowip:
    command: borrowip-mcp
```

When AI agent starts, ask: *"check borrowip status"* → shows your pair code.

### 2. Phone (Termux): Install & connect

```bash
# Install
curl -sL https://raw.githubusercontent.com/wahyuzero/borrowip/main/scripts/install-termux.sh | bash

# Setup (first time only) — choose key or password auth
borrowip init

# Connect using pair code from VPS
borrowip connect BIP-xxxxxx@your-vps-ip
```

### 3. Done!

```text
"Fetch https://example.com using borrowip key BIP-xxxxxx"
```

AI agent routes traffic through your phone's cellular IP automatically.

## MCP Tools

| Tool | Description |
|------|-------------|
| `borrowip_status()` | Show pair code & connected proxies |
| `borrowip_fetch(url, key)` | Fetch URL through mobile proxy |
| `borrowip_check_ip(key)` | Check proxy's external IP |
| `borrowip_list_proxies()` | List all connected proxies |

## Architecture

- **MCP Server** (`borrowip-mcp`): Runs on VPS, auto-started by AI agent via stdio. Generates pair code, manages proxy connections.
- **Client** (`borrowip connect`): Runs on Termux. Starts local SOCKS5 proxy (pproxy), creates SSH reverse tunnel, registers with pair code.

All traffic flows through SSH port 22 — no extra firewall rules.

## Requirements

**VPS:** Python 3.10+, SSH on port 22, AI agent with MCP support (Hermes, Claude, Cursor, etc.)

**Phone:** Android + Termux, Python 3.10+, pproxy (`pip install pproxy`), SSH access to VPS (key or password)

## Installation

### VPS
```bash
git clone https://github.com/wahyuzero/borrowip
cd borrowip && pip install -e .
```

### Termux
```bash
# Quick install
curl -sL https://raw.githubusercontent.com/wahyuzero/borrowip/main/scripts/install-termux.sh | bash

# Or manual
pkg install openssh python
pip install pproxy
git clone https://github.com/wahyuzero/borrowip
cd borrowip && pip install -e ".[client]"
```

## Configuration

### VPS (Hermes `config.yaml`)
```yaml
mcp_servers:
  borrowip:
    command: borrowip-mcp
```

### Termux (`~/.borrowip.toml`)

Created by `borrowip init`. Supports two auth methods:

**Key auth:**
```toml
[server]
host = "your-vps-ip"
user = "your-ssh-user"
ssh_key = "~/.ssh/id_ed25519"
```

**Password auth:**
```toml
[server]
host = "your-vps-ip"
user = "your-ssh-user"
ssh_password = "your-password"
```

Then just run `borrowip connect` (reads config automatically).

## Auto-start (Termux)

```bash
# Install Termux:Boot from F-Droid
mkdir -p ~/.termux/boot/
echo 'borrowip connect &' > ~/.termux/boot/start-borrowip.sh
chmod +x ~/.termux/boot/start-borrowip.sh
```
Tunnel auto-reconnects on drop.

## Security

- SSH key or password auth
- Pair code = identifier only; SSH credentials are the real auth
- All traffic encrypted via SSH
- SOCKS proxy bound to 127.0.0.1 only (not exposed to WiFi)
- Pair code validated (prevents shell injection)

## License

MIT