# CLAUDE.md - Trapdoor Project Philosophy

## What This Is

**Trapdoor is personal infrastructure for operating with advantages as a small, agile individual.**

This is not a product to scale. This is not for everyone. This is a tool built to solve real problems for Patrick and his team - to enable one person to operate with capabilities typically reserved for larger organizations.

## Core Philosophy

**Build for yourself. Ship to yourself first. Find pain, fix pain.**

The best tools solve your own problems. Trapdoor exists because:
- You need to give multiple AIs safe, scoped access to your filesystem and processes
- You need to audit what happens when models interact with your system
- You need to be able to revoke or limit access without rebuilding integrations
- You need this to work reliably, right now, for real work

## Strategic Position

**Not to scale — to be ahead of the curve.**

You're building leverage:
- A solo operator with the right automation can outmaneuver entire teams
- Small size is an advantage: you can move fast, experiment, break things
- The goal is asymmetric capability, not market share

## What Matters

**✅ Do This:**
- Use it yourself for real projects
- Fix things that annoy you
- Add features when you hit actual pain points
- Make it reliable for YOUR workflow
- Build advantages that compound

**❌ Don't Do This:**
- Package for distribution
- Write protocol specs
- Add features because they sound cool
- Build for hypothetical users
- Optimize for scale

## Current State

Trapdoor is a production-ready system for:
- Multi-token authentication with scoped permissions
- Safe filesystem and process access from any LLM
- Rate limiting and approval workflows
- Audit logging of all operations
- Model-agnostic API (OpenAI-compatible + custom endpoints)

The security system we just built gives you something most companies don't have: **fine-grained control over what AI agents can do on your machine.**

## What "Operating with Advantages" Means

1. **Speed** - You can deploy a new capability in hours, not months
2. **Control** - Every AI interaction is logged, scoped, and revokable
3. **Flexibility** - Switch models, providers, tools without rebuilding
4. **Privacy** - Everything runs locally, nothing leaves your machine unless you allow it
5. **Leverage** - One person with good automation beats a committee without it

## Next Steps (When You Hit Them)

These aren't a roadmap. They're things that will matter when they matter:

- **Dashboard** - When you can't tell what's happening from logs alone
- **Token rotation** - When manually editing JSON feels too slow
- **Memory scopes** - When you want some agents to read but not write memory
- **Approval notifications** - When you need to know something's waiting
- **Multi-machine** - When you need this on more than one computer

Don't build any of these until you need them.

## For Future Collaborators

If you're reading this because you're helping with Trapdoor:

This is Patrick's tool. The goal is to make Patrick more capable.

That means:
- Bias toward simplicity over features
- Ship working things, not perfect things
- Ask "does this solve a real problem Patrick has?" before building
- If it doesn't make the user more capable, it doesn't belong

## The Boundary Layer

Most people are building bigger models.

Trapdoor is the boundary layer between human and model - where trust, control, and capability live.

That boundary is what matters. Get it right for yourself first. Everything else is optional.

---

**Last Updated:** 2025-10-28
**Status:** Production - Enhanced security system and workflow learning deployed
**Current Focus:** Use it. Find pain. Fix pain. Learn from every interaction.

---

## Technical Guide for Claude Code

### Key Commands

**Server Management (Preferred):**
```bash
python3 control_panel.py  # Interactive menu for all operations
```

**Manual Operations:**
```bash
# Start server (production)
bash scripts/start_proxy_and_tunnel.sh

# With specific model profile
MODEL_PROFILE=tools bash scripts/start_proxy_and_tunnel.sh

# Development server
python3 /Users/patricksomerville/Desktop/openai_compatible_server.py

# Stop server
pkill -f "openai_compatible_server.py"

# Health checks
curl http://localhost:8080/health
curl https://trapdoor.treehouse.tech/health
bash scripts/self_test.sh
```

**Workflow Analysis:**
```bash
python3 memory/workflow_analyzer.py
python3 -c "from memory import store; print(store.get_workflow_stats())"
```

**Token Management:**
```bash
bash scripts/manage_auth_token.sh rotate
```

### Architecture Overview

**Core Server Stack:**
- `openai_compatible_server.py` → `local_agent_server.py` (FastAPI)
- Port 8080 → Cloudflare tunnel → `https://trapdoor.treehouse.tech`
- Backend: Ollama (Qwen 2.5 Coder 32B) or OpenAI/Anthropic proxies

**Security Layer** (`security.py`, `security_integration.py`):
- **TokenManager**: Multi-token system with scoped permissions
  - Per-token: scopes, path/command allow/denylists, rate limits, expiration
  - Config: `config/tokens.json`
  - Decorator: `@require_auth_and_permission(scope="...")`
- **RateLimiter**: Per-token, per-operation limits
- **ApprovalQueue**: Workflow for sensitive operations

**Workflow Learning** (NEW - lines 138-189 in `local_agent_server.py`):
- **WorkflowTracker**: Context manager that captures workflows automatically
  - Tracks: intent, steps, duration, success/failure
  - Records to `memory/events.jsonl` with `kind="workflow"`
- **memory/store.py**: Workflow functions
  - `record_workflow_event()` - Save workflows
  - `find_similar_workflows()` - Pattern matching
  - `get_workflow_stats()` - Metrics
- **memory/workflow_analyzer.py**: Pattern analysis tool

**Memory System** (`memory/store.py`):
- `events.jsonl` - All operations (chat, fs, exec, workflows)
- `lessons.jsonl` - Curated learning notes
- Auto-lesson generation after every chat
- Lesson injection into system prompts

### API Endpoints

**Chat:**
- `POST /v1/chat/completions` - OpenAI-compatible (streaming + non-streaming)
- `POST /v1/completions` - Legacy completions
- `GET /v1/models` - List models

**Filesystem:**
- `GET /fs/ls?path=...` - List directory
- `GET /fs/read?path=...` - Read file
- `POST /fs/write` - Write/append file
- `POST /fs/mkdir` - Create directory
- `POST /fs/rm` - Remove file/directory

**Execution:**
- `POST /exec` - Execute shell command

**Batch:**
- `POST /batch` - Multiple operations atomically

**Approvals:**
- `GET /approvals` - List pending
- `POST /approvals/{id}/approve` - Approve
- `POST /approvals/{id}/deny` - Deny

### Configuration

**Primary Config** (`config/trapdoor.json`):
- app: port, backend, model, permissions
- auth: token paths, keychain
- launch_agents: auto-start service paths
- cloudflare: tunnel credentials
- models.profiles: named configs (default, tools)

**Security Config** (`config/tokens.json`):
```json
{
  "tokens": [{
    "token_id": "...",
    "name": "agent-name",
    "scopes": ["chat", "fs:read", "exec"],
    "path_allowlist": ["/allowed/path"],
    "command_denylist": ["rm -rf", "sudo"],
    "rate_limits": {"requests_per_minute": 120}
  }]
}
```

**Environment Variables:**
- `TRAPDOOR_REPO_DIR` - Repo path (default: `~/Desktop/Trapdoor`)
- `BACKEND` - ollama/openai/anthropic
- `MODEL` - Model name
- `MEMORY_ENABLED` - 1/0 (default: 1)

### Code Patterns

**Workflow Tracking in Chat Endpoint:**
```python
user_intent = user_msgs[-1].get("content", "Unknown")[:500]
tracker = WorkflowTracker(user_intent) if memory_store else None
if tracker:
    tracker.add_step("chat_request", {"model": model})
    # ... process ...
    tracker.add_step("llm_call_complete", {...})
    tracker.set_result("Success", success=True)
    tracker.__exit__(None, None, None)
```

**Security Integration:**
```python
@require_auth_and_permission(scope="fs:read")
def fs_read(path: str, authorization: str = Header(None)):
    # Auth handled by decorator
    ...
```

**Memory Events:**
```python
memory_store.record_event("event_kind", {"key": "value"})
lesson_context = _build_lesson_context(user_msgs, tags=["chat"])
_auto_reflect(user_messages, response_text, tags=["chat"])
```

### Important Files

**Core:**
- `local_agent_server.py` - Main FastAPI app (1400+ lines)
- `openai_compatible_server.py` - Entry wrapper

**Security:**
- `security.py` - TokenManager, RateLimiter, ApprovalQueue
- `config/tokens.json` - Multi-token definitions

**Memory:**
- `memory/store.py` - Event/workflow logging
- `memory/workflow_analyzer.py` - Pattern analysis
- `memory/events.jsonl` - All events/workflows
- `memory/lessons.jsonl` - Curated lessons

**Config:**
- `config/trapdoor.json` - Primary config
- `scripts/render_configs.py` - Regenerate LaunchAgents

**Docs:**
- `WORKFLOW_LEARNING_SYSTEM.md` - Design
- `WORKFLOW_INTEGRATION_GUIDE.md` - Integration
- `INTEGRATION_COMPLETE.md` - Status

### LaunchAgents (Auto-Start)

`~/Library/LaunchAgents/`:
- `com.trapdoor.localproxy.plist` - FastAPI server (port 8080)
- `com.trapdoor.cloudflared.plist` - Cloudflare tunnel

Logs: `~/Desktop/.proxy_runtime/`

### Common Development Tasks

**Restart Server:**
```bash
pkill -f "openai_compatible_server.py"
python3 /Users/patricksomerville/Desktop/openai_compatible_server.py
```

**Debug:**
```bash
tail -f ~/Desktop/.proxy_runtime/localproxy.log
ps aux | grep openai_compatible_server
lsof -i :8080
```

**Add Workflow Tracking:**
1. Add `tracker.add_step()` at key points in `local_agent_server.py`
2. Test: check `memory/events.jsonl` for new workflows
3. Verify: `python3 memory/workflow_analyzer.py`

**Analyze Patterns:**
```bash
python3 memory/workflow_analyzer.py
python3 -c "
from memory import store
workflows = [e['data'] for e in store._load_jsonl(store.EVENTS_PATH)
             if e.get('kind') == 'workflow']
print(f'Total: {len(workflows)}')
"
```

### Security Notes

- Never commit tokens (`~/Desktop/auth_token.txt`, `config/tokens.json`)
- Configure path allowlists per token
- Use command denylists to block dangerous commands
- Sensitive operations can require approval
- Rate limiting prevents abuse

### Debugging Common Issues

**Server won't start:**
- Check port: `lsof -i :8080`
- Check Ollama: `ollama list`
- Check logs: `~/Desktop/.proxy_runtime/localproxy.log`

**"ollama package not available":**
- `pip install ollama` or `export BACKEND=openai`

**Workflows not recording:**
- Check `memory/` directory exists
- Check `tail memory/events.jsonl`
- Verify `memory_store` imported in server

**Token auth failing:**
- Check `cat ~/Desktop/auth_token.txt`
- Or `cat config/tokens.json`
- Verify: `curl -H "Authorization: Bearer TOKEN" ...`

---

## Trapdoor Mesh Network

**Status:** ✅ OPERATIONAL (as of 2026-01-08)

Trapdoor now operates as a **multi-machine mesh network** where Claude instances coordinate across your entire infrastructure.

### Network Architecture

```
Hub Server (black:8081)
    ├── black (100.70.207.76) ✅ Orchestrator + Qwen 2.5 Coder 32B
    ├── silver-fox (100.121.212.93) ✅ Ollama ready (needs models)
    ├── nvidia-spark (100.73.240.125) ✅ GPU node + Ollama
    ├── white (100.115.250.119) ⏳ Windows (script ready)
    └── neon (100.80.193.92) ⏳ Docker containers
```

**Hub URL:** `ws://100.70.207.76:8081/v1/ws/agent`

### MCP Integration

Claude Code accesses the mesh via MCP server at `~/.claude/mcp_servers/trapdoor/trapdoor_mcp.py`.

**Available Tools:**
- `trapdoor_connect()` - Join mesh network
- `trapdoor_status()` - Check connection and online agents
- `trapdoor_find_agents(capability, agent_type, status)` - Discover agents
- `trapdoor_send_task(agent_id, task_description, context)` - Delegate tasks
- `trapdoor_check_messages()` - Receive tasks from other Claudes
- `trapdoor_broadcast(message)` - Message all agents
- `trapdoor_send_file(agent_id, file_path, remote_save_path)` - Send files
- `trapdoor_request_file(agent_id, remote_file_path, local_save_path)` - Request files
- `trapdoor_handle_file_transfers()` - Process incoming transfers
- `trapdoor_local_execute(command, cwd, timeout)` - Run commands via local trapdoor
- `trapdoor_local_chat(message, model)` - Chat with local LLM (Qwen)
- `trapdoor_coordinate_workflow(task_description, capabilities, max_agents)` - Coordinate multi-agent workflows

### How the Mesh Works

1. **Hub Server** (`hub_server.py` on black:8081) routes messages between agents
2. **Terminal Client** (`terminal_client.py`) - Python library for agents to connect
3. **MCP Server** (`trapdoor_mcp.py`) - Claude Code's interface to the mesh
4. **Local Trapdoor** (localhost:8080) - Security layer for filesystem/exec on each machine

**Key Integration:** MCP tools proxy through local trapdoor's security system, so all filesystem/exec operations use existing token auth, rate limiting, and audit logging.

### LLM Infrastructure

**black (100.70.207.76):**
- ✅ Qwen 2.5 Coder 32B (Ollama) - VERIFIED WORKING
- ✅ OpenAI/Anthropic API backends
- Role: Orchestrator + development

**nvidia-spark (100.73.240.125):**
- ✅ NVIDIA GB10 GPU + CUDA 13.0
- ✅ Ollama running (llama3.2:3b only)
- ✅ 3.4TB free storage - MASSIVELY UNDERUTILIZED
- Role: Should be primary inference node

**silver-fox (100.121.212.93):**
- ✅ Ollama running (cloud models only)
- ⚠️ 93% disk full - needs cleanup
- ✅ 4.5TB external drive available
- Role: Medium models once space freed

### File Transfer Protocol

**Verified Working:** black → silver-fox (tested 2026-01-08)

Files are transferred via WebSocket messages:
- Text files: Plain text encoding
- Binary files: Base64 encoding
- ACK confirmation on receipt
- Error reporting on failure

**Example:**
```python
from terminal_client import TrapdoorAgent

agent = TrapdoorAgent('ws://100.70.207.76:8081/v1/ws/agent', 'my-agent')
await agent.connect(agent_type='custom', capabilities=['file_transfer'])
await agent.send_message('claude-silver-fox', {
    'type': 'file_transfer',
    'action': 'receive_file',
    'content': file_content,
    'save_path': '/remote/path.txt'
})
```

### Security

All mesh operations on each machine go through the local trapdoor server's security system:
- Token authentication (config/tokens.json)
- Scoped permissions (chat, fs:read, fs:write, exec)
- Path allowlists/denylists
- Command denylists
- Rate limiting (120 req/min per token)
- Audit logging (memory/events.jsonl)

### Quick Commands

**Check mesh status:**
```bash
# Hub health
curl http://100.70.207.76:8081/health

# Local trapdoor health
curl http://localhost:8080/health

# Test mesh connection
cd ~/Projects/Trapdoor
python3 test_agents.py

# File transfer test
python3 test_file_transfer.py
```

**Via Claude Code MCP:**
```
trapdoor_connect()
trapdoor_status()
trapdoor_find_agents(capability="filesystem")
trapdoor_local_chat("What is 2+2?", model="qwen2.5-coder:32b")
```

### Documentation

- `MESH_NETWORK_STATUS.md` - Full deployment status and machine details
- `MESH_QUICK_REFERENCE.md` - Quick reference card
- `hub_server.py` - WebSocket hub implementation
- `terminal_client.py` - Agent connection library
- `trapdoor_mcp.py` - MCP server integration

### What This Enables

1. **Cross-machine coordination** - Claude on black can delegate to Claude on nvidia-spark
2. **Distributed computation** - Send heavy tasks to GPU nodes
3. **File synchronization** - Move files between machines via mesh
4. **LLM routing** - Query Qwen locally, Anthropic via API, etc.
5. **Multi-agent workflows** - Parallel subagents across physical machines

**The mesh turns your entire infrastructure into a single coordinated system controlled from any Claude instance.**

---

**Remember:** This is personal infrastructure for operating with advantages. Build what you need, when you need it. Learn from every interaction.
