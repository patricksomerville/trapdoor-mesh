# Cloud Agent Integration Guide

## Important Architecture Note

**Most cloud-based AI agents (ChatGPT Code Interpreter, Claude Code, etc.) run in isolated sandboxes and cannot directly access the open internet.**

This means they **cannot** make direct HTTP requests to your ngrok URL.

## Integration Patterns

### Pattern 1: Direct Connection (For Agents With Internet Access)

Some agents CAN connect directly:
- Local scripts you run
- Agents with unrestricted network access
- Your own custom agents

**For these, just use:**
```
URL:   https://celsa-nonsimulative-wyatt.ngrok-free.dev
Token: 90ac04027a0b4aba685dcae29eeed91a
```

### Pattern 2: Proxy Wrapper (For Sandboxed Agents)

For agents like ChatGPT that run in isolated environments:

**1. Create a proxy wrapper script:**
```python
# trapdoor_proxy.py
import requests

BASE_URL = "https://celsa-nonsimulative-wyatt.ngrok-free.dev"
TOKEN = "90ac04027a0b4aba685dcae29eeed91a"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def chat(message):
    """Send a chat message to Trapdoor"""
    resp = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "qwen2.5-coder:32b",
            "messages": [{"role": "user", "content": message}]
        }
    )
    return resp.json()["choices"][0]["message"]["content"]

def read_file(path):
    """Read a file through Trapdoor"""
    resp = requests.get(
        f"{BASE_URL}/fs/read",
        params={"path": path},
        headers=HEADERS
    )
    return resp.json()

def write_file(path, content):
    """Write a file through Trapdoor"""
    resp = requests.post(
        f"{BASE_URL}/fs/write",
        json={"path": path, "content": content},
        headers=HEADERS
    )
    return resp.json()

def run_command(cmd, cwd="/tmp"):
    """Execute a command through Trapdoor"""
    resp = requests.post(
        f"{BASE_URL}/exec",
        json={"path": cwd, "command": cmd},
        headers=HEADERS
    )
    return resp.json()
```

**2. Upload this script to the sandboxed agent**

**3. Tell the agent:**
```
"I've uploaded a trapdoor_proxy.py module. When I ask you to use the local model,
import that module and call trapdoor_proxy.chat(message)."
```

**4. Usage in the sandbox:**
```python
import trapdoor_proxy

# Chat with local model
response = trapdoor_proxy.chat("What is 2+2?")
print(response)

# Read local file
content = trapdoor_proxy.read_file("/Users/patricksomerville/Desktop/test.txt")

# Write local file
trapdoor_proxy.write_file("/tmp/output.txt", "Hello!")

# Run local command
result = trapdoor_proxy.run_command(["ls", "-la"], cwd="/tmp")
print(result["stdout"])
```

### Pattern 3: Environment Variable Configuration

For agents that support environment variables:

```bash
export TRAPDOOR_URL="https://celsa-nonsimulative-wyatt.ngrok-free.dev"
export TRAPDOOR_TOKEN="90ac04027a0b4aba685dcae29eeed91a"
```

Then in your code:
```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("TRAPDOOR_TOKEN"),
    base_url=f"{os.getenv('TRAPDOOR_URL')}/v1"
)
```

## Who Can Connect Directly vs Needs Proxy

### ✅ Can Connect Directly:
- Your local Python/Node scripts
- Cursor/VSCode with REST client plugins
- Postman/Insomnia API clients
- Local LangChain/LlamaIndex applications
- Custom agents you deploy

### ⚠️ Needs Proxy Wrapper:
- ChatGPT Code Interpreter (sandboxed)
- Claude Code (sandboxed via MCP, but you're already inside my sandbox)
- GitHub Copilot Workspace (sandboxed)
- Most browser-based AI coding assistants

### 🤔 Depends on Configuration:
- Windsurf/Cline/Aider - Check if they allow custom API endpoints
- Replit AI - Depends on their network policies
- Google Colab - Should work (can make external requests)

## Testing Connection

### Quick Test (Any Environment)
```python
import requests

try:
    resp = requests.get(
        "https://celsa-nonsimulative-wyatt.ngrok-free.dev/health",
        timeout=5
    )
    print("✅ Connected:", resp.json())
except Exception as e:
    print("❌ Cannot connect:", e)
    print("This environment needs a proxy wrapper or is blocked from external HTTP")
```

## Security Considerations

1. **Token Management**
   - Your current token has ADMIN scope (full access)
   - Create scoped tokens for untrusted agents
   - Rotate tokens regularly

2. **Network Exposure**
   - ngrok URL is publicly accessible
   - Token is your only authentication
   - Anyone with the token has access to your filesystem

3. **Proxy Scripts**
   - Don't embed tokens in shared scripts
   - Use environment variables
   - Review any code before running in sandboxed environments

## Example: ChatGPT Integration Workflow

**Step 1: Prepare the proxy**
```bash
# On your local machine
cat > trapdoor_proxy.py << 'EOF'
# [paste the proxy wrapper from above]
EOF
```

**Step 2: Upload to ChatGPT**
```
User: "I'm uploading a file called trapdoor_proxy.py. This lets you
connect to my local Trapdoor instance. When I say 'use local model',
import this and call trapdoor_proxy.chat(message)."

[Upload trapdoor_proxy.py]
```

**Step 3: Use it**
```
User: "Use the local model to tell me what 2+2 is"

ChatGPT: [Runs]
import trapdoor_proxy
response = trapdoor_proxy.chat("What is 2+2?")
print(response)
```

## Troubleshooting

**"Connection timeout" or "Cannot reach host"**
→ Your environment is sandboxed. Use the proxy wrapper pattern.

**"Invalid token" errors**
→ Check your token hasn't been rotated. Get current token:
```bash
cat /Users/patricksomerville/Desktop/Trapdoor/config/tokens.json
```

**"ngrok tunnel not found"**
→ Restart Trapdoor via control panel to refresh the tunnel

---

**Bottom Line:**

- **Direct connection:** Use for local scripts and unrestricted environments
- **Proxy wrapper:** Use for ChatGPT, Claude, and other sandboxed agents
- **Your ngrok URL is public** - protect it with token rotation and scoped permissions

---

**Last Updated:** 2025-10-28
**Current Token:** `90ac04027a0b4aba685dcae29eeed91a` (admin scope)
**Current URL:** `https://celsa-nonsimulative-wyatt.ngrok-free.dev`
