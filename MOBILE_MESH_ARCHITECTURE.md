# Trapdoor Mobile Mesh - Neon-Integrated Architecture

## The Vision

**Mobile app as universal remote control for your entire Claude mesh, with Neon as the central nervous system providing memory, orchestration, and intelligence.**

```
┌─────────────────────────────────────────────────────┐
│  iPhone (Trapdoor App)                              │
│  - Voice/Text/Camera Input                          │
│  - Agent Status Dashboard                           │
│  - Push Notifications                               │
│  - Share Sheet Integration                          │
└────────────────────┬────────────────────────────────┘
                     │ WebSocket
                     ↓
┌─────────────────────────────────────────────────────┐
│  Neon (100.80.193.92) - MOTHERSHIP HUB              │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │  Trapdoor Hub (WebSocket Server)           │    │
│  │  - Agent Registry                          │    │
│  │  - Message Bus                             │    │
│  │  - Task Orchestration                      │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │  Memory Systems                            │    │
│  │  ├─ ByteRover (tactical knowledge)         │    │
│  │  ├─ Milvus (semantic search)               │    │
│  │  ├─ Supermemory (archival)                 │    │
│  │  └─ memory.json (knowledge graph)          │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │  Nexus MCP Gateway (70+ tools)             │    │
│  │  - GitHub, Gmail, Slack, Airtable...       │    │
│  └────────────────────────────────────────────┘    │
└──────────────────────┬───────────────────────────────┘
                       │ Tailscale Mesh
        ┌──────────────┼──────────────┬──────────────┐
        ↓              ↓              ↓              ↓
   ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐
   │ black   │   │silver-fox│   │nvidia    │   │browser  │
   │100.70...│   │100.121...│   │100.73... │   │agents   │
   │terminal │   │terminal  │   │inference │   │web ops  │
   └─────────┘   └──────────┘   └──────────┘   └─────────┘
```

## Core Architecture

### Neon Mothership (100.80.193.92)

**Role**: Central nervous system - all intelligence and memory lives here

**Components**:

1. **Trapdoor Hub Service** (New)
   - WebSocket server at `wss://neon.somertime.net:8081/v1/ws/agent`
   - Agent registry (which agents exist, their capabilities, status)
   - Message bus (route requests between agents)
   - Task orchestration (spawn, monitor, coordinate agents)
   - State store (active tasks, conversation context)

2. **Memory Integration**
   - ByteRover: Fast tactical knowledge retrieval
   - Milvus: Semantic search across all interactions
   - Supermemory: Long-term archival
   - Knowledge graph: Structured facts about user preferences

3. **Nexus MCP Gateway**
   - Already running at 100.80.193.92:3000
   - 70+ tools for GitHub, Gmail, Slack, etc.
   - Agents can call these tools through Neon

**New Services to Deploy**:
```yaml
# docker-compose addition
trapdoor-hub:
  image: python:3.12
  volumes:
    - ./trapdoor-hub:/app
  command: python /app/hub_server.py
  ports:
    - "8081:8081"  # WebSocket
    - "8082:8082"  # HTTP API
  environment:
    - BYTEROVER_URL=http://localhost:8100
    - MILVUS_HOST=milvus-standalone
    - MILVUS_PORT=19530
    - NEXUS_URL=http://somertime-nexus:3000
```

### Mobile App (iOS/Android)

**Technology**: React Native (cross-platform) or Swift/Kotlin (native)

**Core Features**:

1. **Control Dashboard**
   ```
   ┌─────────────────────────┐
   │  Trapdoor               │
   │  ━━━━━━━━━━━━━━━━━━━━  │
   │                         │
   │  🟢 4 agents online     │
   │  📊 2 tasks active      │
   │                         │
   │  💬 Quick Actions       │
   │  ┌─────────────────────┐│
   │  │ 🎤 Voice Command    ││
   │  │ 💭 Ask Claude       ││
   │  │ 📸 Process Image    ││
   │  │ 🔗 Handle URL       ││
   │  └─────────────────────┘│
   │                         │
   │  🤖 Active Agents       │
   │  ├─ black-term (busy)   │
   │  │   └─ Backing up...  │
   │  ├─ silverfox (idle)    │
   │  ├─ nvidia (idle)       │
   │  └─ browser-a7 (idle)   │
   │                         │
   │  📋 Active Tasks        │
   │  ├─ ⏳ Backup repos 47% │
   │  │   Tap for details    │
   │  └─ ⏳ Train model 12%   │
   │                         │
   │  📚 Memory Search       │
   │  └─ "How did I..."      │
   │                         │
   │  ⚙️  [Settings]         │
   └─────────────────────────┘
   ```

2. **Input Methods**
   - Text: Type command or question
   - Voice: Siri Shortcuts + in-app voice
   - Camera: Take photo → process with Claude
   - Share Sheet: Share URL/text from any app
   - Files: Upload file for processing

3. **Integrations**
   - **iOS Shortcuts**: "Hey Siri, ask Trapdoor to backup my repos"
   - **Share Sheet**: Share from Safari → "Scrape this with Claude"
   - **Push Notifications**: Task complete, agent offline, errors
   - **Background Refresh**: Maintain WebSocket connection
   - **Face ID/Touch ID**: Secure authentication

4. **Monitoring**
   - Real-time agent status
   - Task progress with live updates
   - Memory search interface
   - Network topology view
   - Logs and audit trail

### Distributed Agents

**Terminal Agents** (Claude Code CLI on various machines):
- black (100.70.207.76): Primary dev machine
- silver-fox (100.121.212.93): Office operations
- white (100.115.250.119): Home automation

**Browser Agents** (Chrome extension, future):
- Web scraping
- OAuth flows
- External network checks

**Inference Agents**:
- nvidia-spark (100.73.240.125): GPU inference for local models
- Neon itself: Ollama/other models

## Memory-Integrated Workflows

### Workflow 1: Memory-Aware Task Execution

```
User (mobile app): "Backup my repos like I did last month"
    ↓
Mobile → Neon Hub → ByteRover search
    "workflow: backup_repos"
    ↓
ByteRover returns:
    "Previous execution 2025-12-08:
     - rsync --exclude node_modules
     - Destination: silver-fox/backups
     - Verified with checksums
     - Duration: 14min"
    ↓
Mobile shows:
    "Found previous workflow. Execute same way? [Yes] [Modify]"
    ↓
User taps [Yes]
    ↓
Neon spawns terminal agent on black with learned parameters
    ↓
Agent executes → Stores to ByteRover:
    "backup_repos_2026-01-08: success, 53 repos, 14min"
    ↓
Push notification:
    "✅ Backup complete. 53 repos → silver-fox"
```

### Workflow 2: Cross-Instance Learning

```
Terminal Claude on black:
    "How did I configure nginx for Trapdoor?"
    ↓
Terminal → Neon Hub → Milvus search
    "nginx configuration trapdoor"
    ↓
Milvus returns top 3 semantic matches:
    1. Trapdoor reverse proxy setup (Oct 2025)
    2. Cloudflare tunnel config (Oct 2025)
    3. SSL certificate renewal (Nov 2025)
    ↓
Terminal Claude:
    "Here's your Trapdoor nginx config from October:
     [shows config with context]"
```

### Workflow 3: Proactive Memory Recall

```
User takes photo of whiteboard with mobile app
    ↓
Mobile → Neon Hub
    "Image analysis + vision model"
    ↓
Neon detects:
    "System architecture diagram with boxes labeled:
     Neon, black, silver-fox, mobile app"
    ↓
Neon searches Milvus:
    "Similar diagrams in: Trapdoor docs, Somertime topology"
    ↓
Mobile shows:
    "This looks like your Trapdoor architecture.
     Add to existing docs or create new?
     [Add to Trapdoor] [Create New] [Just Store]"
    ↓
User taps [Add to Trapdoor]
    ↓
Neon spawns terminal agent on black:
    "Add image + transcription to Trapdoor docs"
    ↓
ByteRover stores:
    "trapdoor_architecture_diagram_2026-01-08"
    ↓
Push notification:
    "✅ Whiteboard added to Trapdoor docs"
```

### Workflow 4: Voice-Initiated Multi-Agent Task

```
User in car: "Hey Siri, ask Trapdoor to clone my new repo idea"
    ↓
Siri Shortcut → Trapdoor app → Neon Hub
    ↓
Neon searches ByteRover:
    "user's repo templates and preferences"
    ↓
ByteRover returns:
    "Preferred structure: /Projects/{name}
     Always init: git, README, .gitignore, LICENSE
     Default license: MIT
     Include: CLAUDE.md template"
    ↓
Mobile shows:
    "Creating repo with your defaults. Name?"
    ↓
User speaks: "Trapdoor mobile app"
    ↓
Neon spawns terminal agent on black:
    "Create repo: trapdoor-mobile-app with learned template"
    ↓
Agent executes:
    - mkdir /Users/patricksomerville/Projects/trapdoor-mobile-app
    - git init
    - Copy templates
    - First commit
    ↓
Stores to ByteRover:
    "repo_created: trapdoor-mobile-app, 2026-01-08"
    ↓
Push notification:
    "✅ Repo ready: ~/Projects/trapdoor-mobile-app"
```

### Workflow 5: Automatic Pattern Learning

```
User repeatedly does:
    "Scrape X and save to Airtable base Y, table Z"

After 3rd execution:
    ↓
Neon analyzes pattern in ByteRover:
    "User always scrapes URLs to same Airtable location"
    ↓
Mobile shows:
    "I noticed you always save scraped data to the
     'Research' base. Make this the default?
     [Yes] [No] [Ask Each Time]"
    ↓
User taps [Yes]
    ↓
ByteRover stores preference:
    "scraping_default_destination: airtable/research"
    ↓
Next time user shares URL:
    "Scrape this"
    ↓
No questions - just executes with learned preference
    ↓
Push notification:
    "✅ Scraped and saved to Research base"
```

## Technical Implementation

### Phase 1: Neon Hub Service (Priority 1)
**Time**: 3-4 hours

**Files to create on Neon**:
```
/data/trapdoor-hub/
├── hub_server.py          # WebSocket + HTTP server
├── agent_registry.py      # Track connected agents
├── message_bus.py         # Route messages between agents
├── task_orchestrator.py   # Spawn and coordinate tasks
├── memory_integration.py  # ByteRover/Milvus interface
└── requirements.txt
```

**Key APIs**:
```python
# WebSocket endpoint
WS /v1/ws/agent
  - Agents connect and register
  - Bidirectional message streaming

# HTTP endpoints
POST /v1/agents/find
  Body: {"capability": "filesystem", "status": "idle"}
  Returns: [agent_id, ...]

POST /v1/tasks/spawn
  Body: {"agent_id": "...", "task": "...", "context": {...}}
  Returns: {"task_id": "...", "status": "starting"}

GET /v1/tasks/{task_id}/stream (SSE)
  Returns: Stream of task updates

POST /v1/memory/search
  Body: {"query": "...", "type": "semantic|keyword"}
  Returns: {results: [...]}

GET /v1/agents
  Returns: [{agent_id, type, capabilities, status}, ...]
```

**Memory Integration**:
```python
# In memory_integration.py
import requests

class MemoryIntegration:
    def __init__(self):
        self.byterover_url = "http://localhost:8100"
        self.milvus_client = MilvusClient(host="milvus-standalone")

    async def search_workflow(self, query: str):
        """Search ByteRover for similar past workflows"""
        response = requests.post(
            f"{self.byterover_url}/retrieve",
            json={"query": query, "top_k": 5}
        )
        return response.json()

    async def search_semantic(self, query: str):
        """Search Milvus for semantic matches"""
        results = self.milvus_client.search(
            collection_name="somertime_knowledge",
            data=[self._embed(query)],
            limit=5
        )
        return results

    async def store_execution(self, workflow_name: str, details: dict):
        """Store successful execution for learning"""
        await self.byterover_client.store({
            "type": "workflow_execution",
            "name": workflow_name,
            "timestamp": time.time(),
            "details": details
        })
```

### Phase 2: Mobile App (Priority 1)
**Time**: 4-6 hours for MVP

**Tech Stack**:
- React Native (cross-platform)
- WebSocket client (reconnecting)
- Push notifications (Firebase Cloud Messaging)
- Secure storage (Keychain/KeyStore)

**Project Structure**:
```
trapdoor-mobile/
├── src/
│   ├── screens/
│   │   ├── Dashboard.tsx
│   │   ├── AgentList.tsx
│   │   ├── TaskMonitor.tsx
│   │   ├── MemorySearch.tsx
│   │   └── Settings.tsx
│   ├── services/
│   │   ├── WebSocketClient.ts
│   │   ├── AuthService.ts
│   │   └── NotificationService.ts
│   ├── components/
│   │   ├── AgentCard.tsx
│   │   ├── TaskProgressCard.tsx
│   │   └── QuickActionButton.tsx
│   └── hooks/
│       ├── useAgents.ts
│       ├── useTasks.ts
│       └── useMemorySearch.ts
├── ios/
└── android/
```

**WebSocket Client**:
```typescript
// src/services/WebSocketClient.ts
import { io, Socket } from 'socket.io-client';

class TrapdoorClient {
  private socket: Socket;
  private token: string;

  constructor(token: string) {
    this.token = token;
    this.connect();
  }

  connect() {
    this.socket = io('wss://neon.somertime.net:8081', {
      auth: { token: this.token },
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000
    });

    this.socket.on('connect', () => {
      console.log('Connected to Neon Hub');
      this.registerMobileAgent();
    });

    this.socket.on('task_update', (update) => {
      this.handleTaskUpdate(update);
    });

    this.socket.on('agent_status', (status) => {
      this.handleAgentStatus(status);
    });
  }

  async registerMobileAgent() {
    this.socket.emit('register', {
      agent_type: 'mobile',
      capabilities: ['user_interface', 'notifications', 'camera', 'voice'],
      device_info: {
        platform: Platform.OS,
        version: DeviceInfo.getVersion()
      }
    });
  }

  async spawnTask(agentId: string, task: string, context: any) {
    return new Promise((resolve, reject) => {
      this.socket.emit('spawn_task',
        { agent_id: agentId, task, context },
        (response) => {
          if (response.error) reject(response.error);
          else resolve(response);
        }
      );
    });
  }

  async findAgent(criteria: any) {
    return new Promise((resolve) => {
      this.socket.emit('find_agent', criteria, (agents) => {
        resolve(agents);
      });
    });
  }

  async searchMemory(query: string) {
    return new Promise((resolve) => {
      this.socket.emit('memory_search', { query }, (results) => {
        resolve(results);
      });
    });
  }
}
```

**Dashboard Screen**:
```typescript
// src/screens/Dashboard.tsx
import React from 'react';
import { View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { useAgents } from '../hooks/useAgents';
import { useTasks } from '../hooks/useTasks';

export function Dashboard() {
  const { agents, onlineCount } = useAgents();
  const { activeTasks } = useTasks();

  const handleVoiceCommand = async () => {
    const result = await VoiceRecognition.start();
    // Send to Neon for processing
  };

  const handleCamera = async () => {
    const photo = await Camera.takePicture();
    // Send to Neon for vision processing
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.status}>
        <Text style={styles.statusText}>
          🟢 {onlineCount} agents online
        </Text>
        <Text style={styles.statusText}>
          📊 {activeTasks.length} tasks active
        </Text>
      </View>

      <View style={styles.quickActions}>
        <QuickActionButton
          icon="🎤"
          label="Voice Command"
          onPress={handleVoiceCommand}
        />
        <QuickActionButton
          icon="💭"
          label="Ask Claude"
          onPress={() => navigation.navigate('Chat')}
        />
        <QuickActionButton
          icon="📸"
          label="Process Image"
          onPress={handleCamera}
        />
      </View>

      <Text style={styles.sectionTitle}>Active Agents</Text>
      {agents.map(agent => (
        <AgentCard key={agent.id} agent={agent} />
      ))}

      <Text style={styles.sectionTitle}>Active Tasks</Text>
      {activeTasks.map(task => (
        <TaskProgressCard key={task.id} task={task} />
      ))}
    </ScrollView>
  );
}
```

### Phase 3: Terminal Agent Integration (Priority 2)
**Time**: 2-3 hours

**Auto-connect on Claude Code start**:
```bash
# ~/.claude/hooks/session_start.sh
#!/bin/bash

# Connect to Neon Hub
python3 ~/.claude/trapdoor_terminal_client.py &

echo "✅ Connected to Trapdoor mesh via Neon"
```

**Terminal Client**:
```python
# ~/.claude/trapdoor_terminal_client.py
import asyncio
import socketio
import os

sio = socketio.AsyncClient()

@sio.event
async def connect():
    print("Connected to Neon Hub")
    await sio.emit('register', {
        'agent_type': 'terminal',
        'hostname': os.uname().nodename,
        'capabilities': ['filesystem', 'git', 'processes', 'mcp_servers'],
        'mcp_tools': get_available_mcp_tools()
    })

@sio.event
async def task_request(data):
    """Handle task request from other agents"""
    task_id = data['task_id']
    task = data['task']
    context = data.get('context', {})

    # Show notification in terminal
    print(f"\n📥 Task from {data['from_agent']}: {task}")

    # Could auto-accept or prompt user
    response = input("Accept? [Y/n]: ")

    if response.lower() != 'n':
        await execute_task(task_id, task, context)

async def execute_task(task_id, task, context):
    """Execute task and stream updates"""
    await sio.emit('task_update', {
        'task_id': task_id,
        'status': 'in_progress',
        'message': 'Starting execution...'
    })

    # Execute via Claude Code or direct execution
    result = await run_claude_code(task, context)

    await sio.emit('task_complete', {
        'task_id': task_id,
        'result': result
    })

async def main():
    await sio.connect('wss://100.80.193.92:8081',
                      auth={'token': os.getenv('TRAPDOOR_TOKEN')})
    await sio.wait()

if __name__ == '__main__':
    asyncio.run(main())
```

### Phase 4: iOS Shortcuts Integration (Priority 3)
**Time**: 1-2 hours

**Shortcuts**:
1. "Ask Trapdoor"
   - Voice input → Send to Neon → Route to appropriate agent

2. "Backup Repos"
   - One-tap backup with learned parameters

3. "Check Trapdoor Status"
   - Quick health check of all agents

4. "Process Screenshot"
   - Take screenshot → Send to vision model → Save result

**Implementation**:
```swift
// In iOS app - expose intents
import Intents

class AskTrapdoorIntent: NSObject, INIntent {
    @NSManaged public var command: String?
}

class AskTrapdoorIntentHandler: NSObject, AskTrapdoorIntentHandling {
    func handle(intent: AskTrapdoorIntent,
                completion: @escaping (AskTrapdoorIntentResponse) -> Void) {
        guard let command = intent.command else {
            completion(AskTrapdoorIntentResponse(code: .failure, userActivity: nil))
            return
        }

        // Send to Neon via WebSocket
        TrapdoorClient.shared.sendCommand(command) { result in
            completion(AskTrapdoorIntentResponse(code: .success, userActivity: nil))
        }
    }
}
```

## Deployment Strategy

### Step 1: Deploy Neon Hub (Weekend 1)
1. SSH to Neon
2. Create `/data/trapdoor-hub/` directory
3. Deploy hub_server.py and dependencies
4. Add to docker-compose
5. Test WebSocket connection from laptop
6. Integrate with ByteRover/Milvus

### Step 2: Build Mobile App MVP (Weekend 2)
1. Init React Native project
2. Build WebSocket client
3. Create Dashboard screen
4. Test agent status display
5. Add task spawning
6. Deploy TestFlight build

### Step 3: Terminal Integration (Weeknight)
1. Create terminal client script
2. Add session_start hook
3. Test bidirectional communication
4. Test task delegation

### Step 4: iOS Shortcuts (Weeknight)
1. Add Intent definitions
2. Create Shortcuts
3. Test voice commands

### Step 5: Polish & Launch (Weekend 3)
1. Push notifications
2. Error handling
3. Reconnection logic
4. Memory search UI
5. Production deploy

## Success Metrics

**It works when**:
- You can spawn a task from your phone while away from computer
- Terminal agents auto-execute with learned parameters from ByteRover
- Push notifications arrive when tasks complete
- Voice commands work reliably
- Memory search finds past workflows instantly
- Average mobile → task execution latency < 2 seconds
- WebSocket connection maintains 99%+ uptime

## Next Steps

Ready to build? Suggested order:

1. **Phase 1**: Deploy Neon Hub (I can help with this remotely)
2. **Phase 2**: Mobile app MVP (dashboard + WebSocket)
3. **Phase 3**: Terminal integration
4. **Phase 4**: iOS Shortcuts
5. **Phase 5**: Polish and launch

Want me to start with Phase 1 - building the Neon Hub service?
