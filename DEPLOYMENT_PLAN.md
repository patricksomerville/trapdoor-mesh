# trapdoor Full Deployment Plan

## Current Status

✅ **Working Now (Locally)**:
- Hub server running on black:8081
- Terminal CLI connects and communicates
- Agent registry and discovery working
- Bidirectional messaging tested
- `/trapdoor` command available in terminal

## Deployment Phases

### Phase 1: Deploy Hub to Neon Mothership
**Goal**: Make hub always-available on the network
**Time**: 30-45 minutes

**Steps**:

1. **Prepare Neon**
   ```bash
   # SSH to Neon
   ssh patrick@100.80.193.92

   # Create directory
   mkdir -p /data/trapdoor-hub
   cd /data/trapdoor-hub
   ```

2. **Copy Files to Neon**
   ```bash
   # From black:
   scp ~/Projects/Trapdoor/hub_server.py patrick@100.80.193.92:/data/trapdoor-hub/
   scp ~/Projects/Trapdoor/requirements.txt patrick@100.80.193.92:/data/trapdoor-hub/
   ```

3. **Create requirements.txt**
   ```txt
   fastapi==0.104.1
   websockets==12.0
   uvicorn==0.24.0
   ```

4. **Create Docker Compose Service**
   ```yaml
   # Add to /data/docker-compose.yml on Neon

   trapdoor-hub:
     image: python:3.12-slim
     container_name: trapdoor-hub
     restart: unless-stopped
     working_dir: /app
     volumes:
       - /data/trapdoor-hub:/app
     ports:
       - "8081:8081"
     command: >
       bash -c "pip install -q -r requirements.txt &&
                python hub_server.py 8081"
     networks:
       - somertime
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
       interval: 30s
       timeout: 10s
       retries: 3
   ```

5. **Deploy and Test**
   ```bash
   # On Neon
   cd /data
   docker-compose up -d trapdoor-hub
   docker logs -f trapdoor-hub

   # Test from black
   curl http://100.80.193.92:8081/health
   ```

6. **Update Default Hub URL**
   ```bash
   # On all machines
   export TRAPDOOR_HUB="ws://100.80.193.92:8081/v1/ws/agent"
   ```

**Verification**:
- [ ] Hub accessible from black
- [ ] Hub accessible from silver-fox
- [ ] Survives Neon restart
- [ ] Health check returns OK

---

### Phase 2: Terminal Auto-Connect on All Machines
**Goal**: Every terminal session auto-connects to mesh
**Time**: 20-30 minutes

**Steps for Each Machine** (black, silver-fox, white):

1. **Install Files**
   ```bash
   # Copy client library
   mkdir -p ~/.claude/scripts
   scp black:~/Projects/Trapdoor/terminal_client.py ~/.claude/scripts/
   scp black:~/.claude/scripts/trapdoor_cli.py ~/.claude/scripts/
   chmod +x ~/.claude/scripts/trapdoor_cli.py

   # Copy skill
   mkdir -p ~/.claude/skills
   scp black:~/.claude/skills/trapdoor.md ~/.claude/skills/
   ```

2. **Create Session Start Hook**
   ```bash
   # Create or edit ~/.claude/hooks/session_start.sh
   cat > ~/.claude/hooks/session_start.sh << 'EOF'
   #!/bin/bash

   # Auto-connect to trapdoor mesh
   export TRAPDOOR_HUB="ws://100.80.193.92:8081/v1/ws/agent"

   # Connect in background
   python3 ~/.claude/scripts/trapdoor_cli.py connect &>/dev/null &

   echo "✓ Connected to trapdoor mesh"
   EOF

   chmod +x ~/.claude/hooks/session_start.sh
   ```

3. **Test**
   ```bash
   # Start new Claude Code session
   claude

   # Should see: "✓ Connected to trapdoor mesh"

   # Test CLI
   python3 ~/.claude/scripts/trapdoor_cli.py status
   python3 ~/.claude/scripts/trapdoor_cli.py agents
   ```

**Verification for Each Machine**:
- [ ] Auto-connects on session start
- [ ] Can see other machines as agents
- [ ] `/trapdoor` command works
- [ ] Can send messages between machines

---

### Phase 3: ByteRover Memory Integration
**Goal**: Agents can search and store to shared memory
**Time**: 1-2 hours

**Steps**:

1. **Add Memory Module to Hub**
   ```python
   # In hub_server.py, add:

   import requests
   from pymilvus import MilvusClient

   # ByteRover client
   BYTEROVER_URL = "http://localhost:8100"

   # Milvus client
   milvus = MilvusClient(host="milvus-standalone", port=19530)

   @app.post("/v1/memory/search")
   async def search_memory(query: str, search_type: str = "semantic"):
       """Search shared memory"""
       if search_type == "workflow":
           # Search ByteRover for past workflows
           response = requests.post(
               f"{BYTEROVER_URL}/retrieve",
               json={"query": query, "top_k": 5}
           )
           return response.json()

       elif search_type == "semantic":
           # Search Milvus
           results = milvus.search(
               collection_name="somertime_knowledge",
               data=[embed(query)],
               limit=5
           )
           return {"results": results}

   @app.post("/v1/memory/store")
   async def store_memory(data: dict):
       """Store to shared memory"""
       # Store to ByteRover
       requests.post(
           f"{BYTEROVER_URL}/store",
           json=data
       )
       return {"status": "stored"}
   ```

2. **Update Terminal Client**
   ```python
   # Add to terminal_client.py:

   async def search_memory(self, query: str, search_type: str = "semantic"):
       """Search shared memory via hub"""
       # Send request to hub
       # Hub queries ByteRover/Milvus
       # Returns results
   ```

3. **Test Cross-Machine Learning**
   ```bash
   # On black: Store a workflow
   python3 << EOF
   import asyncio
   from terminal_client import TrapdoorAgent

   async def test():
       agent = TrapdoorAgent("ws://100.80.193.92:8081/v1/ws/agent")
       await agent.connect()

       # Store workflow
       await agent.store_memory({
           "type": "workflow",
           "name": "backup_repos",
           "steps": ["rsync --exclude node_modules", "verify checksums"],
           "machine": "black",
           "success": True
       })

   asyncio.run(test())
   EOF

   # On silver-fox: Search for workflow
   python3 << EOF
   import asyncio
   from terminal_client import TrapdoorAgent

   async def test():
       agent = TrapdoorAgent("ws://100.80.193.92:8081/v1/ws/agent")
       await agent.connect()

       # Search memory
       results = await agent.search_memory("how to backup repos")
       print(results)

   asyncio.run(test())
   EOF
   ```

**Verification**:
- [ ] Can store workflows from any machine
- [ ] Can search memory from any machine
- [ ] Results include machine context
- [ ] Milvus semantic search works

---

### Phase 4: Chrome Extension Bridge
**Goal**: Browser Claude can orchestrate terminal agents
**Time**: 3-4 hours

**Steps**:

1. **Create Extension Scaffold**
   ```bash
   mkdir -p ~/Projects/trapdoor-extension
   cd ~/Projects/trapdoor-extension
   ```

2. **manifest.json**
   ```json
   {
     "manifest_version": 3,
     "name": "trapdoor",
     "version": "0.1.0",
     "description": "Connect browser Claude to your agent mesh",
     "permissions": ["storage"],
     "host_permissions": [
       "https://claude.ai/*",
       "wss://100.80.193.92:8081/*"
     ],
     "background": {
       "service_worker": "background.js",
       "type": "module"
     },
     "content_scripts": [{
       "matches": ["https://claude.ai/*"],
       "js": ["inject.js"],
       "run_at": "document_end"
     }],
     "action": {
       "default_popup": "popup.html",
       "default_icon": {
         "16": "icons/icon16.png",
         "48": "icons/icon48.png",
         "128": "icons/icon128.png"
       }
     }
   }
   ```

3. **background.js** (WebSocket Client)
   ```javascript
   let ws = null;
   let agents = [];

   // Connect to hub
   function connect() {
     ws = new WebSocket('wss://100.80.193.92:8081/v1/ws/agent');

     ws.onopen = () => {
       // Register as browser agent
       ws.send(JSON.stringify({
         type: 'register',
         agent_id: 'browser-' + Math.random().toString(36).substr(2, 9),
         agent_type: 'browser',
         capabilities: ['web_requests', 'oauth', 'user_prompts'],
         hostname: 'chrome-extension'
       }));
     };

     ws.onmessage = (event) => {
       const msg = JSON.parse(event.data);
       handleMessage(msg);
     };
   }

   // Handle messages from hub
   function handleMessage(msg) {
     if (msg.type === 'registered') {
       console.log('Connected to trapdoor mesh');
     }

     // Forward to content script
     chrome.tabs.query({url: 'https://claude.ai/*'}, (tabs) => {
       tabs.forEach(tab => {
         chrome.tabs.sendMessage(tab.id, msg);
       });
     });
   }

   // Listen for messages from content script
   chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
     if (ws && ws.readyState === WebSocket.OPEN) {
       ws.send(JSON.stringify(msg));
     }
   });

   // Connect on startup
   connect();
   ```

4. **inject.js** (Inject into claude.ai)
   ```javascript
   // Inject trapdoor API into page
   (function() {
     window.trapdoor = {
       async findAgents(criteria = {}) {
         return new Promise((resolve) => {
           chrome.runtime.sendMessage({
             type: 'find_agent',
             criteria
           }, (response) => {
             resolve(response.agents || []);
           });
         });
       },

       async delegateTask(task, criteria = {}) {
         const agents = await this.findAgents(criteria);
         if (agents.length === 0) {
           throw new Error('No agents available');
         }

         return new Promise((resolve) => {
           chrome.runtime.sendMessage({
             type: 'send_message',
             to: agents[0].id,
             payload: { task }
           }, resolve);
         });
       },

       async readFile(path) {
         const agents = await this.findAgents({capability: 'filesystem'});
         if (agents.length === 0) {
           throw new Error('No filesystem agents available');
         }

         return new Promise((resolve) => {
           chrome.runtime.sendMessage({
             type: 'send_message',
             to: agents[0].id,
             payload: { action: 'read_file', path }
           }, (response) => {
             resolve(response.content);
           });
         });
       }
     };

     console.log('✓ trapdoor bridge injected');
   })();
   ```

5. **popup.html** (Status UI)
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <style>
       body {
         width: 300px;
         padding: 16px;
         font-family: system-ui;
       }
       .agent {
         padding: 8px;
         margin: 4px 0;
         border-left: 3px solid #00C853;
       }
       .offline { border-color: #616161; }
     </style>
   </head>
   <body>
     <h2>trapdoor</h2>
     <div id="status">Connecting...</div>
     <div id="agents"></div>
     <script src="popup.js"></script>
   </body>
   </html>
   ```

6. **Load Extension**
   ```
   1. Open Chrome
   2. Go to chrome://extensions
   3. Enable "Developer mode"
   4. Click "Load unpacked"
   5. Select ~/Projects/trapdoor-extension
   ```

7. **Test in Claude.ai**
   ```javascript
   // Open console on claude.ai

   // Find agents
   const agents = await window.trapdoor.findAgents();
   console.log(agents);

   // Delegate task
   await window.trapdoor.delegateTask("list repos", {capability: "filesystem"});

   // Read file
   const content = await window.trapdoor.readFile("/Users/patricksomerville/Projects/Trapdoor/README.md");
   console.log(content);
   ```

**Verification**:
- [ ] Extension loads and connects
- [ ] `window.trapdoor` available in claude.ai console
- [ ] Can find terminal agents from browser
- [ ] Can delegate tasks from browser
- [ ] Terminal agents receive and execute tasks

---

### Phase 5: Update CLAUDE.md Files Across Mesh
**Goal**: All machines understand trapdoor capabilities
**Time**: 30 minutes

**Template Addition for All CLAUDE.md Files**:

```markdown
## trapdoor Agent Mesh

This machine is connected to the trapdoor agent mesh via Neon (100.80.193.92:8081).

### Available Commands

**In Terminal:**
```bash
/trapdoor status              # Show connection and agents
/trapdoor agents              # List all connected agents
/trapdoor delegate <task>     # Delegate task to best agent
/trapdoor send <id> <msg>     # Send message to specific agent
```

**In Code:**
```python
from terminal_client import TrapdoorAgent

agent = TrapdoorAgent()
await agent.connect()

# Find agents
agents = await agent.find_agents(capability="filesystem")

# Delegate task
await agent.send_message(agent_id, {"task": "..."})
```

### Agent Capabilities

**This Machine** ({hostname}):
- `filesystem` - Read/write local files
- `git` - Git operations
- `processes` - Execute commands
- `mcp_servers` - Access to MCP tools

**Other Mesh Agents:**
- `terminal-black` - Primary dev machine
- `terminal-silver-fox` - Office operations
- `terminal-white` - Home automation
- `browser-*` - Web operations, OAuth, external checks

### Cross-Machine Workflows

When you need operations on another machine:
1. Use `/trapdoor agents` to find available agents
2. Use `/trapdoor delegate` to send task automatically
3. Or use Python client for programmatic control

### Memory Integration

All agents share memory via Neon:
- ByteRover: Workflow history and patterns
- Milvus: Semantic search across all interactions
- Supermemory: Long-term archival

Search past workflows:
```python
results = await agent.search_memory("how did I backup repos last time")
```
```

**Deployment Script**:
```bash
#!/bin/bash
# update_claude_md.sh

TEMPLATE="/Users/patricksomerville/Projects/Trapdoor/claude_md_template.md"

# Update on black
cat $TEMPLATE >> /Users/patricksomerville/CLAUDE.md

# Update on silver-fox via SSH
ssh silver-fox "cat >> ~/CLAUDE.md" < $TEMPLATE

# Update on white via SSH
ssh white "cat >> ~/CLAUDE.md" < $TEMPLATE

echo "✓ CLAUDE.md files updated across mesh"
```

**Verification**:
- [ ] All machines have trapdoor section in CLAUDE.md
- [ ] Commands documented correctly
- [ ] Capabilities reflect actual machine setup

---

### Phase 6: End-to-End Testing
**Goal**: Verify full workflow across the mesh
**Time**: 1 hour

**Test Scenarios**:

1. **Terminal → Terminal Communication**
   ```bash
   # On black
   /trapdoor delegate "list repos on silver-fox"

   # Should show repos from silver-fox
   ```

2. **Browser → Terminal Delegation**
   ```javascript
   // In claude.ai console
   const result = await window.trapdoor.delegateTask(
     "backup repos to NAS",
     {capability: "filesystem"}
   );
   console.log(result);
   ```

3. **Memory-Aware Workflow**
   ```bash
   # On black: Run a workflow and store it
   /trapdoor delegate "backup repos with my usual settings"

   # Hub searches ByteRover for "backup repos workflow"
   # Finds past execution with settings
   # Executes with learned parameters
   ```

4. **Cross-Machine File Transfer**
   ```bash
   # On black
   /trapdoor send terminal-silver-fox "copy /data/reports to black:~/Downloads"

   # silver-fox executes rsync to black
   ```

5. **Status Monitoring**
   ```bash
   # On any machine
   /trapdoor agents

   # Should show all connected agents
   # Should reflect current status (idle/busy)
   ```

**Verification**:
- [ ] All machines see each other
- [ ] Can delegate tasks between any two agents
- [ ] Browser can orchestrate terminal agents
- [ ] Memory lookups work across machines
- [ ] Status updates propagate correctly

---

## Rollout Order

1. **Day 1**: Deploy hub to Neon + test locally
2. **Day 2**: Auto-connect black and silver-fox
3. **Day 3**: ByteRover integration
4. **Day 4**: Chrome extension development
5. **Day 5**: Full mesh testing + CLAUDE.md updates

## Success Criteria

The system is fully operational when:
- [ ] Hub runs 24/7 on Neon with <1% downtime
- [ ] All terminal sessions auto-connect to mesh
- [ ] Browser Claude can delegate to terminal agents
- [ ] Agents can search shared memory
- [ ] CLAUDE.md files document trapdoor usage
- [ ] Average message latency <500ms
- [ ] Can orchestrate tasks across 3+ machines
- [ ] Memory lookups return relevant past workflows

## Monitoring

**Hub Health**:
```bash
# Check hub status
curl http://100.80.193.92:8081/health

# Check connected agents
curl http://100.80.193.92:8081/agents

# View logs
ssh patrick@100.80.193.92
docker logs -f trapdoor-hub
```

**Agent Health**:
```bash
# On any machine
/trapdoor status
/trapdoor agents
```

## Troubleshooting

**Hub not accessible**:
- Check Docker: `docker ps | grep trapdoor`
- Check port: `netstat -an | grep 8081`
- Check firewall: Tailscale should allow all mesh traffic

**Agent can't connect**:
- Check TRAPDOOR_HUB env var
- Ping hub: `curl http://100.80.193.92:8081/health`
- Check Tailscale: `tailscale status`

**Messages not routing**:
- Check hub logs
- Verify agent registration: `curl http://100.80.193.92:8081/agents`
- Test WebSocket: `wscat -c ws://100.80.193.92:8081/v1/ws/agent`

---

## What This Enables

Once fully deployed:

**From terminal on black:**
```bash
/trapdoor delegate "train model on nvidia-spark with latest dataset"
```

**From browser Claude:**
```javascript
// Browser Claude realizes it needs local data
const data = await window.trapdoor.readFile("/Users/patricksomerville/data.json");
// Uses it in response without user knowing
```

**From mobile app (future):**
```
"Hey Siri, ask trapdoor to backup my work"
→ Finds black agent
→ Executes backup
→ Push notification: "✓ Backup complete"
```

**The implications**: Any Claude instance anywhere can orchestrate any other Claude instance anywhere else, with shared memory and zero friction.
