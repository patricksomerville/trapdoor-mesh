# trapdoor - What's Working RIGHT NOW

## ✅ Confirmed Working

### 1. Hub Running on Mesh
```bash
$ curl http://100.70.207.76:8081/health
{"status":"ok","agents_connected":0,"agents":[]}
```
- **Location**: black (100.70.207.76:8081)
- **Accessible**: Via Tailscale from entire mesh
- **Features**: Agent registry, message routing, discovery

### 2. Terminal Agents Can Connect
**From black**:
```bash
$ python3 ~/.claude/scripts/trapdoor_cli.py connect
✓ Connected as terminal-black.local
  Hub: ws://100.70.207.76:8081/v1/ws/agent
```

**From silver-fox**:
```bash
$ python3 ~/.claude/scripts/trapdoor_cli.py connect
✓ Connected as terminal-Silver-Fox.local
  Hub: ws://100.70.207.76:8081/v1/ws/agent
```

### 3. Agent Discovery
```bash
$ python3 ~/.claude/scripts/trapdoor_cli.py agents
● terminal-black.local
   Type: terminal
   Capabilities: filesystem, git, processes, mcp_servers
```

### 4. Broadcasting
```bash
$ python3 ~/.claude/scripts/trapdoor_cli.py broadcast "Hello mesh"
✓ Broadcast sent
```

---

## 🔄 What's Not Yet Working (Why)

### Cross-Machine Messaging
**Issue**: CLI connections are short-lived
- Connect → Run command → Disconnect
- Agents need to be simultaneously connected to see each other

**Solution**:
1. Run agents as background daemons (persistent connections)
2. OR: Use Python directly for testing (keeps connections alive)

### Browser Integration
**Status**: Not built yet
**Needs**: Chrome extension (30 min build)

---

## 🎯 To Answer Your Question

> "Say I wanted to use a session in claude.ai to reach into three of my computers and do some complicated thing-- how do we get there?"

### Current State

**Hub**: ✅ Running and accessible
**black**: ✅ Can connect as agent
**silver-fox**: ✅ Can connect as agent
**nvidia-spark**: ⏳ Need to deploy agent
**Chrome**: ❌ Need extension (30 min)

### What You Need

**30-minute Chrome Extension Build:**

1. **Create Extension** (10 min)
   - manifest.json
   - background.js (WebSocket client)
   - inject.js (inject into claude.ai)

2. **Load in Chrome** (5 min)
   - chrome://extensions → Load unpacked

3. **Test** (15 min)
   - Open claude.ai
   - Console: `window.trapdoor.findAgents()`
   - Should see: `[terminal-black, terminal-silver-fox, ...]`

### Then It Works Like This

**In claude.ai console:**
```javascript
// Browser Claude discovers available agents
const agents = await window.trapdoor.findAgents();
// Returns: [
//   {id: "terminal-black", capabilities: ["filesystem", ...]},
//   {id: "terminal-silver-fox", capabilities: [...]},
//   {id: "terminal-nvidia-spark", capabilities: [...]}
// ]

// Delegate task to specific machine
await window.trapdoor.send("terminal-black", {
  task: "read file ~/data.json"
});

// Or auto-find best agent
await window.trapdoor.delegateTask(
  "backup repos",
  {capability: "filesystem"}
);
```

**Browser Claude (in conversation):**
- User: "What's in my Trapdoor README?"
- Claude thinks: "I need to read a file"
- `await window.trapdoor.readFile("/Users/patricksomerville/Projects/Trapdoor/README.md")`
- Extension → Hub → terminal-black
- terminal-black reads file
- Hub → Extension → Browser Claude
- Claude: "Here's what's in your README: ..."

**User never knows two Claudes collaborated.**

---

## The 30-Minute Path to Full Demo

### Step 1: Build Chrome Extension (20 min)

**Files needed:**
```
~/Projects/trapdoor-extension/
├── manifest.json       (5 min)
├── background.js       (10 min)
├── inject.js           (5 min)
└── popup.html          (optional, for status UI)
```

**I can generate all these files right now.**

### Step 2: Deploy nvidia-spark (5 min)

```bash
ssh nvidia-spark "mkdir -p ~/.claude/scripts"
scp terminal_client.py trapdoor_cli.py nvidia-spark:~/.claude/scripts/
ssh nvidia-spark "python3 ~/.claude/scripts/trapdoor_cli.py connect"
```

### Step 3: Test End-to-End (5 min)

**In claude.ai:**
```javascript
const agents = await window.trapdoor.findAgents();
console.log(`Connected to ${agents.length} machines:`, agents.map(a => a.id));

// Send task to nvidia-spark
await window.trapdoor.send("terminal-nvidia-spark", {
  task: "check GPU status"
});
```

---

## What Makes This Insane

Once the extension is built:

**Browser Claude can:**
- Read files from any machine
- Execute commands on any machine
- Coordinate tasks across multiple machines
- All **transparently** in conversation
- User just talks to one Claude
- Claude orchestrates a mesh of agents behind the scenes

**Example:**
```
You in claude.ai: "Train a model with my dataset"

Browser Claude (thinking):
  1. Find dataset → terminal-black has filesystem
  2. Find GPU → terminal-nvidia-spark has GPU
  3. Orchestrate:
     a. Read dataset from black
     b. Send to nvidia-spark
     c. Start training
     d. Monitor progress
     e. Report back to user

"✓ Training started on nvidia-spark with dataset from black"
```

**All automatic. All transparent.**

---

## Ready to Build Extension?

I can generate the complete Chrome extension files right now (3 files, ~200 lines total).

Then you:
1. Create folder: `mkdir ~/Projects/trapdoor-extension`
2. Copy files I generate
3. Load in Chrome
4. Test in claude.ai

30 minutes to full browser → 3 machines coordination.

Want me to generate the extension files?
