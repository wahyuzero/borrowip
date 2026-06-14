# BorrowIP — Guide for AI Agents (LLM Reference)

> **TL;DR:** BorrowIP lets you route HTTP requests through a phone's cellular IP. Use it when a website blocks your server IP (Cloudflare, rate limits, geo-blocks).

## How It Works (3 Roles)

```
📱 Phone (Termux)     →    🖥️ VPS (this server)    →    🤖 You (AI agent)
   borrowip connect          borrowip-mcp runs here        calls MCP tools
   creates SSH tunnel        SOCKS5 ports appear here
   phone's cellular IP       127.0.0.1:10001, :10002...
```

- **Phone** = client. Connects to VPS via SSH reverse tunnel.
- **VPS** = relay. Receives tunnel, exposes SOCKS5 proxy ports.
- **You** = consumer. Use the proxy URL to fetch blocked sites.

## MCP Tools (in order of typical use)

### 1. `borrowip_status()` → Check what's connected
**Always run this first.** Tells you the pair code and lists connected proxies.
```
BorrowIP Status
Pair code: BIP-ab12cd
Proxies: 1 connected
  BIP-xw9su6 | socks5://127.0.0.1:10002 | IP: 140.213.141.84 | alive | 45s ago
```

### 2. `borrowip_get_proxy(key?)` → Get proxy URL
Returns the proxy URL string directly. Use with browser tools.
```
socks5://127.0.0.1:10002 | code=BIP-xw9su6 | IP=140.213.141.84
```
Pass this to: `browser_launch(proxy='socks5://127.0.0.1:10002')`

### 3. `borrowip_fetch(url, key?)` → Fetch a URL
Fetches a URL through the phone's IP. Returns HTML/text.

### 4. `borrowip_health_check(key?)` → Is tunnel alive?
Fast check (3s). Use when `borrowip_fetch` times out or fails.
```
ALIVE: Port 10002 working. External IP: 140.213.141.84
```
or
```
DEAD: Port 10002 not responding. Tunnel dropped. Ask user to reconnect from Termux.
```

### 5. `borrowip_check_ip(key?)` → What IP are we using?
Returns the phone's external cellular IP.

### 6. `borrowip_list_proxies()` → List all proxies
Same info as status but just the proxy list.

## Typical Workflow

```
Step 1: borrowip_status()
  → No proxies? Ask user to run `borrowip connect` on their phone
  → Proxies connected? Continue

Step 2: borrowip_get_proxy()
  → Get the socks5:// URL

Step 3a: For simple fetches → borrowip_fetch(url)
Step 3b: For browser interaction → browser_launch(proxy=<url from step 2>)

Step 4: If fetch/browser fails → borrowip_health_check()
  → DEAD/STALE? Ask user to reconnect
```

## Common Mistakes to Avoid

1. **Don't guess the port.** Always call `borrowip_status()` or `borrowip_get_proxy()` first. The port changes each reconnect (10001, 10002, 10003...).

2. **Don't try to start the server yourself.** The MCP server is already running via your agent's MCP config. You don't need to `start()` anything.

3. **Don't use curl first.** If you have a browser MCP (CloakBrowser, Playwright), launch it with the proxy parameter directly. No need to test with curl separately.

4. **When the tunnel dies, it dies silently.** The SOCKS port stays `LISTEN` but connections timeout. Always use `borrowip_health_check()` to verify — don't assume port open = working.

5. **Ask user to reconnect clearly.** Say: "Please reconnect from Termux: `borrowip connect`" and wait for their confirmation before retrying.

## Using with Browser Tools

### CloakBrowser MCP
```python
# Launch with proxy
browser_launch(proxy="socks5://127.0.0.1:10002")
# Navigate — traffic goes through phone's cellular IP
browser_navigate("https://example.com")
```

### Playwright/Puppeteer (via terminal)
```python
browser = playwright.chromium.launch(
    proxy={"server": "socks5://127.0.0.1:10002"},
    headless=True
)
```

### curl (via terminal)
```bash
curl --socks5-hostname 127.0.0.1:10002 https://example.com
```

## Error Messages Decoded

| Message | Meaning | Action |
|---------|---------|--------|
| `No proxy connected` | No phone connected | Ask user to run `borrowip connect` |
| `Port X not responding` | SSH tunnel dropped | Ask user to reconnect |
| `Fetch failed via port X` | Tunnel dying or site blocking proxy | Run health check, then retry or reconnect |
| `STALE: Port open but cannot reach internet` | Tunnel half-dead | Ask user to reconnect |
