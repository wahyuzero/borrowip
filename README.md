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

## For AI Agents (LLM)

**See [LLM_GUIDE.md](LLM_GUIDE.md)** for a complete reference written for AI agents.

Quick summary of the 3-step workflow:
1. `borrowip_status()` — check what's connected
2. `borrowip_get_proxy()` — get the `socks5://` URL
3. `borrowip_fetch(url)` or `browser_launch(proxy=<url>)` — use the proxy

## MCP Tools

| Tool | Returns | Description |
|------|---------|-------------|
| `borrowip_status()` | Text | Pair code + connected proxies with ports/IPs/alive status. **Run first.** |
| `borrowip_get_proxy(key?)` | `socks5://127.0.0.1:PORT` | Ready-to-use proxy URL. Use with browser tools. |
| `borrowip_fetch(url, key?)` | HTML/text | Fetch a URL through mobile proxy. |
| `borrowip_health_check(key?)` | `ALIVE`/`DEAD`/`STALE` | Fast 3s liveness test. Use when fetch fails. |
| `borrowip_check_ip(key?)` | IP address | Phone's external cellular IP. |
| `borrowip_list_proxies()` | Text | List all proxies with details. |

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