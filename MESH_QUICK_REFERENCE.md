# Trapdoor Mesh Network - Quick Reference Card

**Date**: 2026-01-08
**Hub**: ws://100.70.207.76:8081/v1/ws/agent

---

## Network Map

```
Hub (black:8081)
  ├─ black (100.70.207.76) - Qwen 2.5 Coder 32B
  ├─ silver-fox (100.121.212.93) - Ollama ready
  ├─ nvidia-spark (100.73.240.125) - GPU + 3.4TB
  ├─ white (100.115.250.119) - Windows
  └─ neon (100.80.193.92) - Docker
```

---

## MCP Tools (via Claude Code)

### Discovery
```
trapdoor_connect()
# Connect this Claude to mesh

trapdoor_status()
# Check connection and see online agents

trapdoor_find_agents(capability="filesystem")
# Find agents with specific capability
```

### File Transfer
```
trapdoor_send_file(
  agent_id="claude-silver-fox",
  file_path="/path/to/file.txt",
  remote_save_path="/remote/path/file.txt"
)
# Send file to another machine

trapdoor_request_file(
  agent_id="claude-black",
  remote_file_path="/path/on/black.txt",
  local_save_path="./local.txt"
)
# Request file from another machine

trapdoor_handle_file_transfers()
# Process incoming file transfers
```

### Task Delegation
```
trapdoor_send_task(
  agent_id="claude-nvidia-spark",
  task_description="Check GPU status and available models",
  context="Need to know if nvidia-spark is ready for inference"
)
# Delegate task to another Claude

trapdoor_check_messages()
# Check for incoming tasks from other Claudes

trapdoor_broadcast("Starting maintenance")
# Broadcast message to all agents
```

### Local Operations (on machines with trapdoor server)
```
trapdoor_local_execute(
  command=["nvidia-smi"],
  cwd="/home/patrick",
  timeout=30
)
# Execute command on local machine via trapdoor

trapdoor_local_chat(
  message="What is 2+2?",
  model="qwen2.5-coder:32b"
)
# Chat with local Qwen model
```

### Coordination
```
trapdoor_coordinate_workflow(
  task_description="Backup all repositories",
  required_capabilities="filesystem,git",
  max_agents=3
)
# Find suitable agents and plan workflow
```

---

## Terminal Usage (Python)

```python
from terminal_client import TrapdoorAgent
import asyncio

async def demo():
    # Connect
    agent = TrapdoorAgent(
        'ws://100.70.207.76:8081/v1/ws/agent',
        'my-agent-id'
    )

    await agent.connect(
        agent_type='custom',
        capabilities=['filesystem', 'test'],
        hostname='my-machine'
    )

    # Find agents
    agents = await agent.find_agents()
    print(f"Found {len(agents)} agents")

    # Send message
    await agent.send_message('claude-silver-fox', {
        'task': 'List files in ~/Projects'
    })

    # Broadcast
    await agent.broadcast({
        'message': 'Hello mesh!'
    })

    await agent.ws.close()

asyncio.run(demo())
```

---

## LLM Resources by Machine

### black (100.70.207.76)
- **Qwen 2.5 Coder 32B** ✅ (via Ollama, VERIFIED)
- OpenAI API backend
- Anthropic API backend
- Local trapdoor: http://localhost:8080
- Use for: Fast local inference, code tasks

### nvidia-spark (100.73.240.125)
- **Ollama running** (systemd service)
- **GPU**: NVIDIA GB10 + CUDA 13.0
- **Storage**: 3.4TB free
- Current models: llama3.2:3b (tiny!)
- Use for: Large model inference, GPU acceleration
- **Status**: Underutilized - needs more models!

### silver-fox (100.121.212.93)
- **Ollama running**
- **Disk**: 93% full (needs cleanup!)
- Current: Only cloud models (remote API)
- External: 4.5TB drive available
- Use for: Medium models (once space freed)

---

## Common Workflows

### Test Connection
```bash
# From black:
cd ~/Projects/Trapdoor
python3 test_agents.py

# Check what's online:
python3 -c "
from terminal_client import TrapdoorAgent
import asyncio

async def check():
    agent = TrapdoorAgent('ws://100.70.207.76:8081/v1/ws/agent', 'checker')
    await agent.connect(agent_type='test', capabilities=[])
    agents = await agent.find_agents()
    print(f'Online: {[a[\"id\"] for a in agents]}')
    await agent.ws.close()

asyncio.run(check())
"
```

### Send File Between Machines
```bash
# From black to silver-fox:
python3 test_file_transfer.py

# Custom transfer:
python3 << 'EOF'
import asyncio
from terminal_client import TrapdoorAgent

async def transfer():
    agent = TrapdoorAgent('ws://100.70.207.76:8081/v1/ws/agent', 'sender')
    await agent.connect(agent_type='test', capabilities=['file_transfer'])

    # Read file
    content = open('/path/to/file.txt', 'r').read()

    # Send
    await agent.send_message('claude-silver-fox', {
        'type': 'file_transfer',
        'action': 'receive_file',
        'content': content,
        'encoding': 'text',
        'save_path': '/remote/path.txt'
    })

    await asyncio.sleep(2)
    await agent.ws.close()

asyncio.run(transfer())
EOF
```

### Check Models on Remote Machine
```bash
# Via SSH:
ssh patrick@100.73.240.125 "ollama list"

# Via mesh (future):
# Use trapdoor_send_task to ask remote Claude
# to check models and report back
```

---

## Configuration Files

### MCP Server Config
```json
# ~/.claude/mcp_servers/trapdoor/config.json
{
  "command": "python3",
  "args": ["/path/to/trapdoor_mcp.py"],
  "env": {
    "TRAPDOOR_HUB": "ws://100.70.207.76:8081/v1/ws/agent",
    "TRAPDOOR_LOCAL_URL": "http://localhost:8080"
  }
}
```

### Trapdoor Server
```bash
# Start local trapdoor (if not running):
python3 /Users/patricksomerville/Desktop/openai_compatible_server.py

# Check status:
curl http://localhost:8080/health
```

---

## Troubleshooting

### Agent Not Connecting
```bash
# Check hub is running:
curl http://100.70.207.76:8081/health

# Check WebSocket connection:
python3 -c "
import asyncio, websockets, json

async def test():
    async with websockets.connect('ws://100.70.207.76:8081/v1/ws/agent') as ws:
        await ws.send(json.dumps({'type': 'register', 'agent_id': 'test'}))
        response = await ws.recv()
        print(f'Hub response: {response}')

asyncio.run(test())
"
```

### File Transfer Failed
```bash
# Check receiver is listening:
# On silver-fox:
python3 test_file_receiver.py

# Then send from black:
python3 test_file_transfer.py
```

### Local Trapdoor Not Responding
```bash
# Check if running:
lsof -i :8080

# Check Ollama:
ollama list

# Restart:
pkill -f openai_compatible_server.py
python3 /Users/patricksomerville/Desktop/openai_compatible_server.py &
```

---

## Quick Commands

```bash
# Hub status
curl http://100.70.207.76:8081/health

# Local trapdoor status
curl http://localhost:8080/health

# List mesh machines
tailscale status | grep -E "(black|silver|nvidia|white|neon)"

# SSH to machines
ssh patrick@100.121.212.93     # silver-fox
ssh patrick@100.73.240.125     # nvidia-spark
ssh patrick@100.115.250.119    # white
ssh patrick@100.80.193.92      # neon

# Check models on nvidia-spark
ssh patrick@100.73.240.125 "ollama list"

# Test file transfer
cd ~/Projects/Trapdoor
python3 test_file_transfer.py
```

---

## Next Steps

1. **Pull models to nvidia-spark**:
   ```bash
   ssh patrick@100.73.240.125
   ollama pull qwen2.5-coder:7b
   ollama pull llama3.3:70b
   ollama pull deepseek-r1:7b
   ```

2. **Free space on silver-fox**:
   ```bash
   ssh patrick@100.121.212.93
   # Clean ~/Downloads, move large files
   # Then: ollama pull qwen2.5-coder:7b
   ```

3. **Complete deployments**:
   - white: Run `deploy_to_white.py`
   - neon: Copy files to Docker container

4. **Set up Big Daddy orchestrator**:
   - Give Deepseek/Opus your trapdoor token
   - Let it coordinate the entire mesh

---

**Quick Start**: Open Claude Code with MCP, run `trapdoor_connect()`, then use other tools to coordinate across your mesh!
