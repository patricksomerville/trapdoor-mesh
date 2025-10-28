# ChatGPT Proxy Guide

## Why This Exists

ChatGPT runs in a sandboxed environment that **cannot make outbound HTTPS requests** to arbitrary URLs like your ngrok tunnel.

This proxy creates a local bridge that ChatGPT can potentially access.

## Setup

### Step 1: Start the Proxy (On Your Machine)

```bash
cd /Users/patricksomerville/Desktop/Trapdoor
python3 chatgpt_proxy.py
```

You should see:
```
============================================================
ChatGPT Proxy for Trapdoor
============================================================

Testing Trapdoor connection...

✅ Connected to Trapdoor
   Backend: ollama
   Model: qwen2.5-coder:32b

✅ Proxy ready!

Upload chatgpt_proxy_client.py to ChatGPT, then:

  import chatgpt_proxy_client as proxy
  proxy.chat('Hello!')
  proxy.ls('/Users/patricksomerville/Desktop')

============================================================

 * Running on http://0.0.0.0:5000
```

### Step 2: Upload Client to ChatGPT

Upload `chatgpt_proxy_client.py` to ChatGPT

### Step 3: Tell ChatGPT How to Use It

```
I've uploaded chatgpt_proxy_client.py. This connects you to my local Trapdoor instance
via a proxy running on localhost:5000.

Import it as:
  import chatgpt_proxy_client as proxy

Available functions:
  - proxy.chat("prompt") - Chat with local model
  - proxy.ls("/path") - List directory
  - proxy.read("/path/to/file") - Read file
  - proxy.write("/path", "content") - Write file
  - proxy.exec(["ls", "-la"], cwd="/tmp") - Run command
  - proxy.health() - Check connection

When I say "use local model" or "check my Desktop", use these functions.
```

### Step 4: Test It

Tell ChatGPT:
```
Test the connection to my local Trapdoor instance
```

ChatGPT should run:
```python
import chatgpt_proxy_client as proxy
status = proxy.health()
print(status)
```

## API Endpoints

The proxy exposes these endpoints on `http://localhost:5000`:

| Endpoint | Method | Body/Query | Returns |
|----------|--------|------------|---------|
| `/health` | GET | - | Proxy and Trapdoor status |
| `/chat` | POST | `{"prompt": "..."}` | `{"response": "..."}` |
| `/ls` | GET | `?path=/path` | `{"files": [...]}` |
| `/read` | GET | `?path=/path/to/file` | `{"content": "..."}` |
| `/write` | POST | `{"path": "...", "content": "..."}` | `{"status": "ok"}` |
| `/exec` | POST | `{"cmd": [...], "cwd": "..."}` | `{"stdout": "...", "stderr": "...", "returncode": 0}` |
| `/mkdir` | POST | `{"path": "..."}` | `{"status": "ok"}` |
| `/rm` | POST | `{"path": "..."}` | `{"status": "ok"}` |

## Testing Locally

```bash
# Test health
curl http://localhost:5000/health

# Test chat
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'

# Test ls
curl "http://localhost:5000/ls?path=/Users/patricksomerville/Desktop"

# Test exec
curl -X POST http://localhost:5000/exec \
  -H "Content-Type: application/json" \
  -d '{"cmd": ["echo", "hello"], "cwd": "/tmp"}'
```

## Important Notes

### Limitation: ChatGPT Might Still Not Access This

Even with a local proxy, ChatGPT's sandbox might not allow connections to `localhost:5000`.

If ChatGPT still can't connect, you'll need:
- A different cloud-hosted proxy (defeats the purpose)
- OR expose Trapdoor through OpenRouter
- OR just accept ChatGPT can't use it

### Who CAN Use the Proxy

- Other local tools running on your machine
- Scripts you run in terminal
- Jupyter notebooks
- Local development environments
- **Possibly** ChatGPT (if their sandbox allows localhost)

### Who DOESN'T Need the Proxy

Anyone with direct internet access can use Trapdoor directly:
```
URL:   https://celsa-nonsimulative-wyatt.ngrok-free.dev
Token: 90ac04027a0b4aba685dcae29eeed91a
```

No proxy needed for:
- curl
- Python scripts with `requests` or `openai` SDK
- Node.js applications
- Postman/Insomnia
- Most AI coding assistants (Cursor, Windsurf, etc.)

## Troubleshooting

**"Connection refused" from ChatGPT:**
→ Their sandbox blocks localhost connections. Proxy won't work for them.

**"Cannot connect to Trapdoor" when starting proxy:**
→ Make sure Trapdoor is running (`python3 control_panel.py`)

**Proxy starts but ChatGPT gets errors:**
→ Check proxy logs in terminal for details

---

**Bottom Line:**

This proxy is a **workaround for ChatGPT's sandbox limitations**. Everyone else can connect to Trapdoor directly without it.

---

**Files:**
- `chatgpt_proxy.py` - Flask server (run this on your machine)
- `chatgpt_proxy_client.py` - Upload this to ChatGPT
- `trapdoor_connector.py` - Direct connector (no proxy needed)

**Created:** 2025-10-28
