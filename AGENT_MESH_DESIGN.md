# Trapdoor Agent Mesh - Deep Integration Design

## Vision

Transform Trapdoor from an API bridge into a **unified Claude mesh** where any Claude instance (browser or terminal) can seamlessly orchestrate any other instance, bidirectionally.

## Architecture Components

### 1. Trapdoor Hub (WebSocket Server)

**Location**: Runs on black (this machine) at `wss://trapdoor.treehouse.tech/v1/ws/agent`

**Core Services**:
- **Agent Registry**: Tracks all connected Claude instances
- **Message Bus**: Routes messages between agents
- **State Store**: Shared context and task state
- **Capability Discovery**: Find agents by what they can do

**Agent Registration**:
```json
{
  "agent_id": "browser-a7f3",
  "type": "browser",
  "capabilities": ["web_requests", "oauth_flows", "user_interaction", "screenshots"],
  "status": "idle",
  "last_seen": 1704814320,
  "user_id": "patrick"
}
```

### 2. Chrome Extension (Browser Agent)

**Functionality**:
- Auto-connects to Trapdoor Hub via WebSocket
- Registers as browser agent with capabilities
- Listens for task requests from terminal agents
- Can spawn/coordinate terminal agents
- Injects Trapdoor API into claude.ai page context

**Key Features**:
- Token storage in extension storage
- Real-time agent status display
- Task execution in browser context (fetch, OAuth, user prompts)
- Visual dashboard of active agents and tasks

### 3. Terminal Integration (Claude Code)

**Auto-Connection**:
- Session start hook auto-connects to Hub
- Registers as terminal agent
- Monitors inbox for tasks from other agents
- Can request help from browser agents

**Capabilities**:
- Filesystem operations
- Git operations
- Process management
- MCP server access
- Network operations

### 4. Shared State Layer

**Purpose**: Allow agents to share context seamlessly

**State Keys**:
- `tasks/{task_id}`: Task metadata and progress
- `context/{conversation_id}`: Shared conversation context
- `files/{checksum}`: File metadata for transfers
- `agents/{agent_id}`: Agent status and metrics

**Example**:
```json
{
  "tasks/task-xyz": {
    "description": "Copy repos to NAS",
    "created_by": "browser-a7f3",
    "assigned_to": "terminal-3f2",
    "status": "in_progress",
    "progress": "47/53 repos",
    "messages": [
      {"from": "browser-a7f3", "time": 1704814320, "text": "Starting copy"},
      {"from": "terminal-3f2", "time": 1704814325, "text": "Processing repo 1/53"}
    ],
    "context": {
      "user_intent": "Backup before vacation",
      "constraints": ["skip node_modules", "verify checksums"]
    }
  }
}
```

## Message Protocol

### Message Types

#### 1. Task Request
```json
{
  "type": "task_request",
  "task_id": "task-xyz",
  "from": "browser-a7f3",
  "to": "terminal-3f2",
  "task": {
    "description": "Copy repos to NAS",
    "context": {...},
    "stream_updates": true,
    "callback_channel": "browser-a7f3-inbox"
  }
}
```

#### 2. Help Request
```json
{
  "type": "help_request",
  "from": "terminal-3f2",
  "capability_needed": "web_request",
  "task": "Check if trapdoor.treehouse.tech is accessible",
  "urgency": "immediate"
}
```

#### 3. Task Update
```json
{
  "type": "task_update",
  "task_id": "task-xyz",
  "status": "in_progress",
  "progress": "47/53 repos",
  "message": "Processing repositories..."
}
```

#### 4. Agent Discovery
```json
{
  "type": "find_agent",
  "criteria": {
    "capability": "filesystem",
    "status": "idle",
    "type": "terminal"
  }
}
```

## Seamless Workflow Patterns

### Pattern 1: Capability-Based Delegation

**When**: Browser Claude needs filesystem access

```javascript
// Browser Claude automatically does this:
const agent = await trapdoor.findAgent({capability: "filesystem"});
const result = await trapdoor.delegate({
  to: agent.id,
  task: "Read ~/.config/trapdoor/settings.json",
  wait_for_result: true
});
```

### Pattern 2: Assistance Request

**When**: Terminal Claude needs external network verification

```python
# Terminal Claude MCP tool does this:
result = await trapdoor.request_help(
    capability="web_request",
    task="Check https://trapdoor.treehouse.tech/health",
    return_type="status_code_and_latency"
)
```

### Pattern 3: Multi-Agent Orchestration

**When**: Complex task needs both browser and terminal

```javascript
// Browser Claude orchestrates:
const workflow = await trapdoor.orchestrate({
  agents_needed: ["terminal", "browser"],
  steps: [
    {agent: "terminal", task: "Write monitoring script"},
    {agent: "browser", task: "Get Slack webhook URL from user"},
    {agent: "terminal", task: "Deploy as systemd service"},
    {agent: "browser", task: "Verify test alert in Slack"}
  ],
  parallel_where_possible: true
});
```

### Pattern 4: Context Handoff

**When**: Browser Claude wants terminal agent to take over completely

```javascript
// Full context transfer:
await trapdoor.handoff({
  to_agent: "terminal-3f2",
  conversation_id: "conv-xyz",
  context: {
    user_intent: "Backup all work",
    constraints: [...],
    files_discussed: [...],
    decisions_made: [...]
  },
  take_over: true  // Terminal agent becomes primary
});
```

## Security Model

### Token Scopes

Each agent gets token with appropriate scopes:

**Browser Agent Token**:
```json
{
  "scopes": ["agent:register", "agent:discover", "task:create", "state:read"],
  "capabilities": ["web_requests", "user_interaction"],
  "rate_limits": {"requests_per_minute": 60}
}
```

**Terminal Agent Token**:
```json
{
  "scopes": ["agent:register", "task:execute", "fs:read", "fs:write", "exec"],
  "capabilities": ["filesystem", "processes", "git"],
  "rate_limits": {"requests_per_minute": 120}
}
```

### Approval System

High-risk operations still require approval:
- File deletion (rm -rf)
- Sudo commands
- Network-exposed services
- Data exfiltration (large file uploads)

## Visual Dashboard

Web UI at `trapdoor.treehouse.tech/dashboard`:

```
┌─────────────────────────────────────────────────────┐
│  Trapdoor Agent Mesh - Live Dashboard               │
├─────────────────────────────────────────────────────┤
│  🌐 Active Agents (3)                               │
│  ├─ browser-a7f3 (idle) [web, oauth, prompts]       │
│  ├─ terminal-3f2 (busy) [fs, git, mcp]              │
│  └─ terminal-9c1 (idle) [processes, network]        │
│                                                      │
│  📋 Active Tasks (1)                                 │
│  └─ task-xyz "Copy repos to NAS"                    │
│     Created by: browser-a7f3                         │
│     Assigned to: terminal-3f2                        │
│     Status: 47/53 repos (89%)                        │
│     [View Details] [Kill] [Pause]                    │
│                                                      │
│  💬 Recent Messages (last 10)                        │
│  09:15:23 terminal-3f2 → browser-a7f3                │
│           "Transfer 89% complete, 6 repos remain"    │
│  09:14:18 browser-a7f3 → terminal-3f2                │
│           "Task delegated: Copy repos to NAS"        │
│  09:13:02 terminal-9c1 → hub                         │
│           "Registered with capabilities: processes"  │
│                                                      │
│  📊 Stats                                            │
│  Tasks completed today: 47                           │
│  Average task time: 2m 34s                           │
│  Most active agent: terminal-3f2 (31 tasks)          │
└─────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: WebSocket Hub (Priority 1)
**Time**: 2-3 hours

Files to create/modify:
- `/Users/patricksomerville/scripts/local_agent_server.py` (add WebSocket endpoint)
- Create: `agent_registry.py` (agent management)
- Create: `message_bus.py` (routing logic)
- Create: `state_store.py` (shared state)

**Endpoints**:
- `WS /v1/ws/agent` - Agent connection
- `POST /v1/agents/find` - Discovery
- `GET/PUT /v1/state/{key}` - State access
- `GET /v1/agents` - List agents

### Phase 2: Chrome Extension (Priority 1)
**Time**: 2-3 hours

Files to create:
- `chrome-extension/manifest.json`
- `chrome-extension/background.js` (WebSocket client)
- `chrome-extension/inject.js` (inject into claude.ai)
- `chrome-extension/popup.html` (status UI)

**Features**:
- Auto-connect on extension load
- Register as browser agent
- Inject `window.trapdoor` API
- Visual agent status panel
- Token management

### Phase 3: Terminal Integration (Priority 2)
**Time**: 1-2 hours

Files to create:
- `~/.claude/hooks/session_start.sh` (auto-connect)
- Create MCP server: `mcp_trapdoor_mesh.py`
- Create: `terminal_agent_client.py` (WebSocket client)

**Features**:
- Auto-register on Claude Code start
- Monitor inbox for tasks
- MCP tools for delegation
- Background connection maintenance

### Phase 4: Dashboard (Priority 2)
**Time**: 1-2 hours

Files to create:
- `static/dashboard.html`
- `static/dashboard.js`
- `static/dashboard.css`

**Features**:
- Real-time agent list
- Task monitoring
- Message stream
- Agent metrics

### Phase 5: Polish & Testing (Priority 3)
**Time**: Ongoing

- Error handling + reconnection logic
- Task persistence (survive restarts)
- Capability-based routing optimization
- Multi-user support (future)
- Load testing
- Documentation

## Example User Experiences

### Experience 1: "Just Works" Delegation

```
User (in browser): "Update all my CLAUDE.md files across the network"

Browser Claude:
  1. Realizes it needs filesystem + network access
  2. Finds terminal agent on black
  3. Delegates task with context
  4. Terminal agent finds all CLAUDE.md files
  5. Makes updates across mesh network
  6. Reports back: "✅ Updated 7 CLAUDE.md files across 4 machines"

User sees: Single response, no context switch needed
```

### Experience 2: Proactive Assistance

```
User (in terminal): "Check if my Trapdoor tunnel is working"

Terminal Claude:
  1. Checks localhost:8080 ✅
  2. Realizes external check would be better
  3. Finds browser agent
  4. Requests external check
  5. Browser agent executes from real external IP
  6. Reports: "✅ Tunnel works. Accessible in 127ms from LA"

User sees: Comprehensive answer, automatic collaboration
```

### Experience 3: Complex Orchestration

```
User (in browser): "Monitor Trapdoor and alert me on Slack if down"

Browser Claude orchestrates automatically:
  - Spawns 3 terminal agents in parallel
  - Coordinates between terminal (script) and browser (Slack setup)
  - Tests end-to-end
  - Reports when deployed

User sees: One coherent response, mesh handled complexity
```

## Key Innovations

1. **Capability Discovery**: Agents find each other by what they can do, not by hardcoded names

2. **Context Handoff**: Full conversation context flows between agents seamlessly

3. **Bidirectional**: Either terminal or browser can initiate, both are peers

4. **Transparent**: User doesn't think about "browser vs terminal" - it's just "Claude"

5. **Observable**: Dashboard shows what's happening in real-time

6. **Composable**: Agents can orchestrate multiple other agents for complex workflows

## Success Metrics

**Seamlessness achieved when**:
- User can't tell which agent did the work
- Context never gets lost in handoffs
- Tasks complete without user intervention
- Agents collaborate automatically when needed
- Average handoff latency < 500ms

## Next Steps

1. ✅ Design complete (this document)
2. Build Phase 1: WebSocket Hub
3. Build Phase 2: Chrome Extension
4. Test bidirectional flows
5. Build Phase 3: Terminal integration
6. Build Phase 4: Dashboard
7. Polish and documentation

---

**Status**: Design phase complete, ready for implementation
**Last Updated**: 2026-01-08
**Architecture**: Bidirectional agent mesh with WebSocket hub
