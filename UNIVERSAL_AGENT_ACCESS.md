# Trapdoor: Universal AI Agent Local Access

**The Big Idea:** Give ANY frontier AI model access to your local machine through a single OpenAI-compatible endpoint.

---

## 🚀 The Power of OpenAI Compatibility

Trapdoor speaks the OpenAI API protocol. This means **every AI agent in existence** that supports OpenAI can now access your local machine:

### Frontier Models
- ✅ **Claude** (Anthropic) - Via custom base URL
- ✅ **GPT-4/o1** (OpenAI) - Via proxy/wrapper
- ✅ **Gemini** (Google) - Via OpenAI SDK compatibility
- ✅ **Llama models** (Meta) - Already local via Ollama
- ✅ **Grok** (xAI) - Via OpenAI-compatible endpoint
- ✅ **Mistral** - Via OpenAI-compatible wrapper

### Coding Assistants
- ✅ **Cursor** - Custom model configuration
- ✅ **GitHub Copilot** - Enterprise proxy setup
- ✅ **Cody** (Sourcegraph) - Custom LLM endpoint
- ✅ **Continue.dev** - Direct config
- ✅ **Aider** - Custom model URL
- ✅ **Tabby** - OpenAI-compatible backend

### Agent Frameworks
- ✅ **LangChain** - ChatOpenAI with custom base_url
- ✅ **AutoGPT** - Custom LLM provider
- ✅ **BabyAGI** - OpenAI client configuration
- ✅ **CrewAI** - Custom LLM setup
- ✅ **Semantic Kernel** - Custom endpoint
- ✅ **LlamaIndex** - Custom LLM configuration

### No-Code/Low-Code Platforms
- ✅ **Zapier AI** - Custom webhook actions
- ✅ **Make.com** - HTTP module with OpenAI format
- ✅ **n8n** - OpenAI node with custom URL
- ✅ **Flowise** - Custom LLM configuration
- ✅ **LangFlow** - Custom model endpoint

---

## 🎯 What You Get

**For ANY AI Agent:**

1. **Local LLM Access**
   - Qwen 2.5 Coder 32B running on your hardware
   - No API costs, no rate limits on chat
   - Full privacy - nothing leaves your machine

2. **Filesystem Control**
   - Read/write/list files on your local machine
   - Create directories, manage projects
   - Full file system access with authentication

3. **Command Execution**
   - Run any shell command remotely
   - Execute scripts, run builds, deploy code
   - Full system control via authenticated endpoints

4. **Memory System**
   - Automatic learning from interactions
   - Context injection from previous sessions
   - Progressive improvement over time

---

## 🔧 Universal Configuration Pattern

### The Magic URL Pattern

```bash
# Chat endpoint (OpenAI-compatible)
https://your-trapdoor-url.com/v1/chat/completions

# Tool endpoints (Trapdoor-specific, need auth)
https://your-trapdoor-url.com/fs/ls
https://your-trapdoor-url.com/fs/read
https://your-trapdoor-url.com/fs/write
https://your-trapdoor-url.com/exec
```

**Your URLs:**
- **Ngrok (active):** `https://celsa-nonsimulative-wyatt.ngrok-free.dev`
- **Cloudflare (stable):** `https://trapdoor.treehouse.tech`

---

## 💡 Real-World Use Cases

### 1. Claude Desktop with Local File Access

```json
// Claude Desktop custom model config
{
  "models": [
    {
      "name": "Local Qwen + Files",
      "provider": "openai",
      "api_key": "not-needed",
      "base_url": "https://trapdoor.treehouse.tech/v1",
      "model": "qwen2.5-coder:32b"
    }
  ]
}
```

Now Claude can:
- Chat using your local Qwen model
- Access your filesystem via custom instructions
- Run commands on your machine

### 2. Cursor with Local Context

```json
// Cursor settings.json
{
  "cursor.model": "openai/custom",
  "cursor.customModel": {
    "endpoint": "https://trapdoor.treehouse.tech/v1/chat/completions",
    "apiKey": "dummy"
  }
}
```

Cursor now:
- Uses your local model for code completion
- Can read your entire codebase via Trapdoor
- Executes commands to run tests/builds

### 3. LangChain Local Agent

```python
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool
import requests

# Connect to your local LLM
llm = ChatOpenAI(
    openai_api_base="https://trapdoor.treehouse.tech/v1",
    openai_api_key="not-needed",
    model_name="qwen2.5-coder:32b"
)

# Add Trapdoor tools
def read_local_file(path: str) -> str:
    response = requests.get(
        "https://trapdoor.treehouse.tech/fs/read",
        params={"path": path},
        headers={"Authorization": "Bearer 90ac04027a0b4aba685dcae29eeed91a"}
    )
    return response.text

def exec_command(cmd: str) -> str:
    response = requests.post(
        "https://trapdoor.treehouse.tech/exec",
        json={"cmd": cmd.split()},
        headers={"Authorization": "Bearer 90ac04027a0b4aba685dcae29eeed91a"}
    )
    return response.json()["stdout"]

tools = [
    Tool(
        name="ReadFile",
        func=read_local_file,
        description="Read a file from the local filesystem"
    ),
    Tool(
        name="ExecuteCommand",
        func=exec_command,
        description="Execute a shell command"
    )
]

# Now ANY LangChain agent can access your local machine
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
result = agent.run("Read my package.json and tell me what dependencies I have")
```

### 4. AutoGPT with Local Access

```python
# AutoGPT config
class TrapdoorLLM:
    def __init__(self):
        self.base_url = "https://trapdoor.treehouse.tech/v1"
        self.token = "90ac04027a0b4aba685dcae29eeed91a"

    def chat(self, messages):
        # Use local LLM
        response = requests.post(
            f"{self.base_url}/chat/completions",
            json={"messages": messages}
        )
        return response.json()

    def execute_command(self, cmd):
        # Execute on local machine
        response = requests.post(
            "https://trapdoor.treehouse.tech/exec",
            json={"cmd": cmd},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()

# AutoGPT now runs entirely on your local infrastructure
```

### 5. n8n Workflow with Local Execution

```json
// n8n workflow node
{
  "name": "Chat with Local LLM",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "https://trapdoor.treehouse.tech/v1/chat/completions",
    "sendBody": true,
    "bodyParameters": {
      "messages": [
        {"role": "user", "content": "{{ $json.prompt }}"}
      ]
    }
  }
}

// Then execute result
{
  "name": "Execute Command Locally",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "https://trapdoor.treehouse.tech/exec",
    "authentication": "headerAuth",
    "headerAuth": {
      "name": "Authorization",
      "value": "Bearer 90ac04027a0b4aba685dcae29eeed91a"
    },
    "sendBody": true,
    "bodyParameters": {
      "cmd": "{{ $json.command.split(' ') }}"
    }
  }
}
```

---

## 🌟 The Universal Agent Pattern

**Any AI agent can now:**

```
1. Agent asks question
   ↓
2. Local LLM (Qwen) responds via Trapdoor
   ↓
3. Agent needs file? → Trapdoor /fs/read with auth
   ↓
4. Agent needs to execute? → Trapdoor /exec with auth
   ↓
5. Result goes back to agent
   ↓
6. Agent continues with local context
```

---

## 🔐 Security Model

### Two-Tier Access

**Chat Endpoint (No Auth):**
- `/v1/chat/completions` - Open to all agents
- Safe: Just LLM inference, no system access
- Rate limit: Unlimited

**Tool Endpoints (Auth Required):**
- `/fs/*` - Requires Bearer token
- `/exec` - Requires Bearer token
- Rate limit: 120 req/60s per token

### Why This Works

Agents can:
1. **Chat freely** with your local LLM (no risk)
2. **Request tool use** but you control who gets access (token required)
3. **Audit everything** (logs in `.proxy_runtime/audit.log`)

---

## 📊 Comparison: Cloud vs Local

### Traditional Setup (Cloud-Only)
```
Agent → OpenAI API ($$$) → Response
       ❌ No local file access
       ❌ No local command execution
       ❌ All data leaves your machine
       ❌ API costs per request
```

### With Trapdoor (Universal Local Access)
```
Agent → Trapdoor → Local LLM → Response
                 ↳ Local Files (with auth)
                 ↳ Local Commands (with auth)
       ✅ Everything stays local
       ✅ Zero API costs for chat
       ✅ Full system control
       ✅ Works with ANY OpenAI-compatible agent
```

---

## 🎨 Example: Connect OpenAI ChatGPT to Your Local Machine

Yes, even ChatGPT can access your local machine through custom actions:

```json
// ChatGPT Custom GPT Action
{
  "openapi": "3.0.0",
  "info": {
    "title": "Local Machine Access",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://trapdoor.treehouse.tech"
    }
  ],
  "paths": {
    "/fs/read": {
      "get": {
        "operationId": "readFile",
        "summary": "Read a file from my local machine",
        "parameters": [
          {
            "name": "path",
            "in": "query",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "security": [{"bearerAuth": []}]
      }
    },
    "/exec": {
      "post": {
        "operationId": "executeCommand",
        "summary": "Execute a command on my local machine",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "cmd": {
                    "type": "array",
                    "items": {"type": "string"}
                  }
                }
              }
            }
          }
        },
        "security": [{"bearerAuth": []}]
      }
    }
  },
  "components": {
    "securitySchemes": {
      "bearerAuth": {
        "type": "http",
        "scheme": "bearer"
      }
    }
  }
}
```

Now ChatGPT can:
- Read files from your Desktop
- Execute commands on your machine
- Access your local development environment

**All through the web interface!**

---

## 🚀 Quick Start for Any Agent

### Step 1: Get Your Trapdoor URL

```bash
# Check active tunnel
cat /Users/patricksomerville/Desktop/Trapdoor/.proxy_runtime/public_url.txt
```

Current: `https://celsa-nonsimulative-wyatt.ngrok-free.dev`

### Step 2: Configure Your Agent

**For chat-only access (any agent):**
```
Base URL: https://celsa-nonsimulative-wyatt.ngrok-free.dev/v1
Model: qwen2.5-coder:32b
API Key: not-needed (but some clients require a dummy value)
```

**For tool access (filesystem, exec):**
```
Auth Token: 90ac04027a0b4aba685dcae29eeed91a
Header: Authorization: Bearer <token>
```

### Step 3: Test It

```python
import requests

# Test chat
response = requests.post(
    "https://celsa-nonsimulative-wyatt.ngrok-free.dev/v1/chat/completions",
    json={"messages": [{"role": "user", "content": "Hello!"}]}
)
print(response.json())

# Test filesystem (with auth)
response = requests.get(
    "https://celsa-nonsimulative-wyatt.ngrok-free.dev/fs/ls",
    params={"path": "/Users/patricksomerville/Desktop"},
    headers={"Authorization": "Bearer 90ac04027a0b4aba685dcae29eeed91a"}
)
print(response.json())
```

---

## 💎 The Killer Use Case

**Imagine this workflow:**

1. **ChatGPT** (or Claude, or Gemini) asks you a question
2. You say "check my local project files"
3. **ChatGPT uses Trapdoor** to read your actual project files
4. ChatGPT suggests code changes
5. You say "write those changes"
6. **ChatGPT uses Trapdoor** to write to your local files
7. You say "run the tests"
8. **ChatGPT uses Trapdoor** to execute `pytest`
9. Tests pass, ChatGPT confirms success

**All from the ChatGPT web interface. No copying files, no context limits, no local setup.**

This is the future of AI development tools.

---

## 🎯 Next Steps

### 1. Fix the Server (Immediate)
```bash
pkill -f "openai_compatible_server.py"
python3 control_panel.py  # Stop then Start
```

### 2. Connect Your First Agent (Today)

Pick ANY agent you use:
- Configure the base URL
- Add your token for tools
- Start building

### 3. Build Agent Tools (This Week)

Create wrappers for your favorite agents:
```python
class TrapdoorToolkit:
    """Universal toolkit for any AI agent"""

    def read_file(self, path):
        """Read local file"""

    def write_file(self, path, content):
        """Write local file"""

    def execute(self, cmd):
        """Execute command"""

    def chat(self, message):
        """Chat with local LLM"""
```

### 4. Share Your Setup (Long-term)

This is a **universal pattern**:
- Any developer can run Trapdoor
- Any AI agent can connect
- Everyone gets local-first AI development

---

## 📖 Summary

**Trapdoor isn't just a tool - it's a protocol.**

The OpenAI API format is the universal language of AI agents. By speaking that language and adding local execution capabilities, Trapdoor becomes a bridge between **every AI agent** and **your local machine**.

This means:
- ✅ Use GPT-4 with local file access
- ✅ Use Claude with local command execution
- ✅ Use Gemini with your local codebase
- ✅ Use ANY agent with ANY local resource

**One endpoint. Universal compatibility. Unlimited possibilities.**

---

**Ready to connect the world's best AI models to your local machine?**

