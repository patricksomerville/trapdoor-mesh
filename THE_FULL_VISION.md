# trapdoor - The Full Vision: AI Mesh Network

## What We Just Built

**An AI coordination mesh** where:
- Multiple Claude Code instances run on different machines
- Each Claude can think, plan, and execute independently
- They communicate through a central hub
- Browser Claude can orchestrate all of them
- Tasks flow seamlessly across the network

## Architecture

```
Browser Claude (claude.ai)
  ↓ Chrome Extension
  ↓ WebSocket to Hub

Hub (black:8081)
  ├─ Routes messages
  ├─ Tracks agent capabilities
  └─ Enables discovery

Claude Code Instances:
  ├─ black: Full AI with filesystem, git, processes
  ├─ silver-fox: Full AI with filesystem, git, processes
  └─ nvidia-spark: Full AI with GPU, training capabilities

Each Claude:
  - Has full reasoning capability
  - Can make decisions
  - Executes on its local machine
  - Coordinates with other Claudes
```

## How It Actually Works

### Example 1: Browser Claude Orchestrates Multi-Machine Task

**You in claude.ai:**
> "I need to train a model. The dataset is on black, and nvidia-spark has the GPU."

**Browser Claude thinks:**
1. I need dataset from black
2. I need GPU on nvidia-spark
3. Let me coordinate this

**Browser Claude executes:**
```javascript
// Find Claude instances
const agents = await window.trapdoor.findAgents();

// Send task to Claude on black
await window.trapdoor.send("claude-black", {
  task: "Prepare dataset from ~/data/training_data.csv",
  deliver_to: "claude-nvidia-spark"
});

// Send task to Claude on nvidia-spark
await window.trapdoor.send("claude-nvidia-spark", {
  task: "Receive dataset and train model",
  expect_data_from: "claude-black"
});
```

**Claude Code on black thinks:**
- *I need to prepare this dataset*
- *Let me read it, validate it, clean it*
- *Then send to nvidia-spark*
- [Executes data prep]
- [Sends to nvidia-spark Claude]

**Claude Code on nvidia-spark thinks:**
- *I'm receiving a dataset*
- *Let me validate it's what I expected*
- *Check GPU availability*
- *Start training with optimal hyperparameters*
- [Executes training]
- [Reports progress back to browser Claude]

**Browser Claude reports to you:**
> "✓ Dataset prepared on black (10k samples, validated)
> ✓ Training started on nvidia-spark (GPU 0, batch_size=32)
> ✓ ETA: 45 minutes
> I'll notify you when complete."

**All automatic. All intelligent. All coordinated.**

---

### Example 2: Claude Code Instances Coordinate Directly

**You in terminal on black:**
> "I need the latest logs from silver-fox combined with my local logs for analysis"

**Claude Code on black (this instance) thinks:**
- *I need logs from silver-fox*
- *Let me ask the Claude there to get them*

```python
# Claude uses trapdoor MCP tool
trapdoor_send_task(
  "claude-silver-fox",
  "Get system logs from the last hour and send them back"
)
```

**Claude Code on silver-fox receives:**
- *Another Claude needs logs*
- *Let me figure out which logs are relevant*
- [Executes: finds logs, filters, compresses]
- [Sends back to black]

**Claude Code on black receives logs:**
- *Got the remote logs*
- *Now let me combine with my local logs*
- *Analyze for patterns*
- [Presents analysis to you]

**No human coordination needed. The Claudes figured it out.**

---

### Example 3: Mobile App Future State

**You on iPhone:**
> "Hey Siri, ask trapdoor to backup my work"

**Mobile app:** *Opens connection to hub*

**Finds:** claude-black, claude-silver-fox

**Mobile sends to hub:**
```json
{
  "task": "Coordinate backup of Patrick's work to NAS",
  "priority": "high"
}
```

**Hub routes to claude-black (best match for task)**

**Claude Code on black thinks:**
- *Backup task, high priority*
- *Let me figure out what needs backing up*
- *Check what changed since last backup*
- *Coordinate with silver-fox for NAS access*

**Claude on black delegates to silver-fox:**
```python
trapdoor_send_task(
  "claude-silver-fox",
  "Prepare NAS at /backups/patrick-work-2026-01-08",
  context="I'll be sending ~15GB via rsync"
)
```

**Both Claudes coordinate the backup**

**Mobile receives:**
> Push notification: "✓ Backup complete. 47 repos, 8.2GB, verified checksums"

**All autonomous. All intelligent. All coordinated.**

---

## The Tools Available to Each Claude

When a Claude Code instance has trapdoor MCP tools, it can:

### Discovery
```python
trapdoor_find_agents(capability="git")
# Returns: [claude-black, claude-silver-fox, ...]
```

### Task Delegation
```python
trapdoor_send_task(
  "claude-silver-fox",
  "Check disk space and clean up old backups if needed"
)
# Claude on silver-fox thinks about this and executes intelligently
```

### Coordination
```python
trapdoor_coordinate_workflow(
  "Synchronize repositories across all machines",
  required_capabilities="git,filesystem",
  max_agents=3
)
# Finds suitable Claudes and creates coordination plan
```

### Status Checking
```python
trapdoor_check_messages()
# See tasks from other Claudes

trapdoor_status()
# Current mesh status
```

### Broadcasting
```python
trapdoor_broadcast("Starting system maintenance")
# All Claudes on mesh receive this
```

---

## What Makes This Different

### Traditional Multi-Agent Systems
```
Orchestrator (dumb)
  ↓ sends explicit commands
Workers (dumb)
  ↓ execute exactly what told
  ↓ no thinking
Done
```

### trapdoor AI Mesh
```
Coordinator Claude (AI)
  ↓ sends task description

Worker Claudes (AI)
  ↓ think about task
  ↓ plan execution
  ↓ adapt to local conditions
  ↓ coordinate with each other
  ↓ execute intelligently

Report back with insights
```

**Every node is intelligent. Every node can adapt. Every node can coordinate.**

---

## Deployment Status

### ✅ Working Now

1. **Hub** - Running on black:8081, accessible via Tailscale
2. **MCP Server** - Built, provides trapdoor tools to Claude Code
3. **Terminal Client** - Python agent library
4. **CLI** - Command-line interface for testing

### ⏳ 30 Minutes to Full Demo

1. **Deploy MCP to silver-fox and nvidia-spark** (10 min)
   ```bash
   # Copy files
   scp trapdoor_mcp.py silver-fox:~/.claude/mcp_servers/trapdoor/
   scp config.json silver-fox:~/.claude/mcp_servers/trapdoor/

   # Repeat for nvidia-spark
   ```

2. **Build Chrome Extension** (15 min)
   - manifest.json
   - background.js (WebSocket client)
   - inject.js (inject into claude.ai)
   - Load in Chrome

3. **Test End-to-End** (5 min)
   - Start Claude Code on black (has trapdoor tools)
   - Start Claude Code on silver-fox (has trapdoor tools)
   - Open claude.ai with extension
   - Demonstrate 3-way coordination

---

## The Demo Script

### Test 1: Claude to Claude
```
Terminal on black (Claude Code):
  "Use trapdoor to ask the Claude on silver-fox
   what its disk usage is"

Claude on black:
  [Uses trapdoor_send_task]

Claude on silver-fox:
  [Receives task, checks disk, responds]

Claude on black:
  "Claude on silver-fox reports: 245GB used of 500GB (49%)"
```

### Test 2: Browser Orchestrates Multiple Claudes
```
Browser claude.ai:
  "Find all Python files modified today across
   my machines and show me the summary"

Browser Claude:
  [Finds claude-black, claude-silver-fox]
  [Sends task to each]

Both Claudes:
  [Search their local filesystems]
  [Send results back]

Browser Claude:
  "Found 23 Python files modified today:
   - black: 15 files (mostly in ~/Projects/Trapdoor)
   - silver-fox: 8 files (various projects)
   Would you like details on any specific files?"
```

### Test 3: Complex Multi-Machine Workflow
```
Browser claude.ai:
  "Deploy my latest code from black to silver-fox
   and run the tests there"

Browser Claude:
  [Coordinates both Claudes]

Claude on black:
  [Commits latest changes]
  [Pushes to silver-fox]

Claude on silver-fox:
  [Pulls latest code]
  [Runs test suite]
  [Reports results]

Browser Claude:
  "✓ Deployed and tested
   - 47 files updated
   - All 23 tests passed
   - Ready for production"
```

---

## Why This Is Insane

1. **Multiple AIs thinking simultaneously**
   - Not executing commands, but reasoning about problems
   - Each adapts to its local environment
   - Each makes intelligent decisions

2. **Seamless coordination**
   - No manual SSH/rsync/scp
   - No explicit commands
   - Just: "I need this done" → AIs figure it out

3. **Transparent to user**
   - You talk to one Claude (browser)
   - That Claude orchestrates others
   - You get unified results
   - Never know multiple AIs collaborated

4. **Scales infinitely**
   - Add more machines → add more Claudes
   - Each joins the mesh automatically
   - Instant coordination capability

5. **Intelligent adaptation**
   - Claudes learn from each other
   - Share knowledge via ByteRover/Milvus
   - Get smarter over time

---

## Next Step

**Want me to complete the deployment?**

30 minutes to:
1. Deploy MCP server to silver-fox
2. Build Chrome extension
3. Run the full 3-way demo (Browser → black → silver-fox)

**This is the real deal. This is the insane part working.**
