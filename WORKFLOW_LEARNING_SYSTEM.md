# Trapdoor Workflow Learning System

**Goal:** Turn every Qwen interaction into valuable learning material for smoother future workflows.

---

## 🎯 The Problem You've Identified

You're already using Trapdoor with cloud agents. It works. But:
- ❌ Qwen doesn't learn from successful workflows
- ❌ Common patterns aren't recognized
- ❌ You repeat the same multi-step processes
- ❌ No optimization from past interactions

**You want:** Qwen to remember "when user asks X, do workflow Y" based on actual usage.

---

## 💡 What to Capture

### 1. Successful Command Sequences

**Example interaction:**
```
User: "Check the project status"
Qwen executes:
1. /fs/ls → /Users/patricksomerville/Desktop/Projects/MyApp
2. /fs/read → package.json
3. /exec → git status
4. /exec → npm test
5. Synthesizes: "Project is on branch main, 3 tests passing, dependencies up to date"
```

**What to learn:**
- Pattern: "check project status" = [ls, read package.json, git status, npm test]
- Context: This workflow worked well
- Frequency: How often is this requested?
- Variations: What similar requests map to this workflow?

### 2. Multi-Step Workflows

**Example:**
```
User: "Deploy to staging"
Qwen executes:
1. git pull
2. npm run build
3. npm test
4. scp dist/* user@staging:/var/www/
5. ssh user@staging 'systemctl restart app'
```

**What to learn:**
- This is an atomic workflow (all steps must succeed)
- Dependencies between steps
- Error handling points
- Common variations

### 3. Tool Usage Patterns

**Example:**
```
When user mentions "weather" → curl weather API
When user mentions "stock" + ticker → curl finance API
When user says "search" → use web_fetch.py + grep
When user says "analyze code" → delegate to GPT-4
```

**What to learn:**
- Intent → Tool mapping
- Which tools work best for which tasks
- When to delegate vs handle locally

### 4. Error Recovery Patterns

**Example:**
```
User: "Run the tests"
Qwen: /exec → npm test
Error: "Cannot find module 'jest'"
Qwen: /exec → npm install
Qwen: /exec → npm test
Success!
```

**What to learn:**
- Common errors and fixes
- Automatic recovery steps
- When to ask user vs auto-fix

---

## 🔧 Implementation: Learning Pipeline

### Phase 1: Enhanced Event Capture (Today)

**Upgrade `memory/store.py`** to capture workflow context:

```python
# memory/store.py additions

def record_workflow_event(
    intent: str,
    steps: List[Dict[str, Any]],
    result: str,
    success: bool,
    duration: float
) -> None:
    """Record a complete workflow execution"""
    workflow = {
        "ts": time.time(),
        "intent": intent,  # User's original request
        "steps": steps,    # All commands executed
        "result": result,  # Final outcome
        "success": success,
        "duration": duration,
        "tags": _extract_tags(intent, steps)
    }
    _append(EVENTS_PATH, {"kind": "workflow", "data": workflow})

def _extract_tags(intent: str, steps: List[Dict]) -> List[str]:
    """Auto-tag workflows based on content"""
    tags = []

    # Detect patterns
    if any("git" in str(step) for step in steps):
        tags.append("git")
    if any("npm" in str(step) or "package.json" in str(step) for step in steps):
        tags.append("nodejs")
    if any("test" in str(step) for step in steps):
        tags.append("testing")
    if any("deploy" in intent.lower() for step in steps):
        tags.append("deployment")

    # Add more pattern detection
    return tags

def find_similar_workflows(intent: str, limit: int = 5) -> List[Dict]:
    """Find workflows similar to current intent"""
    workflows = [
        e["data"] for e in _load_jsonl(EVENTS_PATH)
        if e.get("kind") == "workflow"
    ]

    # Score by intent similarity and success
    scored = []
    intent_tokens = set(intent.lower().split())

    for wf in workflows:
        wf_tokens = set(wf["intent"].lower().split())
        similarity = len(intent_tokens & wf_tokens) / len(intent_tokens | wf_tokens)

        # Boost successful workflows
        score = similarity * (1.5 if wf["success"] else 0.5)

        scored.append((score, wf))

    scored.sort(reverse=True)
    return [wf for score, wf in scored[:limit]]
```

### Phase 2: Workflow Recognition (This Week)

**Add to `local_agent_server.py`:**

```python
# Track current workflow
_current_workflow = None

def _start_workflow_tracking(user_intent: str):
    """Begin tracking a new workflow"""
    global _current_workflow
    _current_workflow = {
        "intent": user_intent,
        "steps": [],
        "start_time": time.time()
    }

def _add_workflow_step(operation: str, command: Dict, result: Dict):
    """Add a step to current workflow"""
    if _current_workflow:
        _current_workflow["steps"].append({
            "operation": operation,
            "command": command,
            "result": result,
            "timestamp": time.time()
        })

def _complete_workflow(final_result: str, success: bool):
    """Complete and save workflow"""
    if _current_workflow:
        duration = time.time() - _current_workflow["start_time"]
        memory_store.record_workflow_event(
            intent=_current_workflow["intent"],
            steps=_current_workflow["steps"],
            result=final_result,
            success=success,
            duration=duration
        )
        _current_workflow = None

# Integrate into chat endpoint
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    # Extract user intent
    user_messages = [m for m in request.messages if m.role == "user"]
    if user_messages:
        intent = user_messages[-1].content
        _start_workflow_tracking(intent)

    # Check for similar past workflows
    similar_workflows = memory_store.find_similar_workflows(intent, limit=3)

    # Inject workflow context into system prompt
    if similar_workflows:
        workflow_context = _format_workflow_suggestions(similar_workflows)
        # Add to messages...

    # ... rest of chat handling ...

    # Track completion
    _complete_workflow(response_text, success=True)
```

### Phase 3: Workflow Suggestions (This Week)

**Enhance system prompt with learned workflows:**

```python
def _format_workflow_suggestions(workflows: List[Dict]) -> str:
    """Format past successful workflows as suggestions"""
    if not workflows:
        return ""

    suggestions = ["Based on similar past requests, you previously:"]

    for wf in workflows:
        steps_summary = " → ".join([
            f"{step['operation']}({step['command'].get('path', step['command'].get('cmd', [''])[0])})"
            for step in wf["steps"][:5]  # First 5 steps
        ])

        suggestions.append(
            f"- For '{wf['intent']}': {steps_summary} "
            f"(took {wf['duration']:.1f}s, {'succeeded' if wf['success'] else 'failed'})"
        )

    suggestions.append("\nConsider following a similar workflow if appropriate.")
    return "\n".join(suggestions)
```

### Phase 4: Automatic Workflow Execution (Next Week)

```python
def _can_auto_execute_workflow(intent: str, threshold: float = 0.9) -> Optional[Dict]:
    """Check if workflow can be auto-executed based on confidence"""
    similar = memory_store.find_similar_workflows(intent, limit=1)

    if not similar:
        return None

    workflow = similar[0]

    # Calculate confidence
    intent_tokens = set(intent.lower().split())
    wf_tokens = set(workflow["intent"].lower().split())
    similarity = len(intent_tokens & wf_tokens) / len(intent_tokens | wf_tokens)

    # Check if workflow was successful multiple times
    recent_executions = memory_store.count_workflow_executions(
        workflow["intent"],
        days=30
    )

    success_rate = memory_store.get_workflow_success_rate(workflow["intent"])

    if similarity > threshold and recent_executions >= 3 and success_rate > 0.9:
        return workflow

    return None

# In chat endpoint
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    intent = extract_user_intent(request.messages)

    # Check for auto-executable workflow
    auto_workflow = _can_auto_execute_workflow(intent)

    if auto_workflow:
        # Add to system prompt
        system_addition = f"""
        HIGH CONFIDENCE WORKFLOW DETECTED:
        This request matches a workflow you've successfully executed {auto_workflow['execution_count']} times.

        Suggested workflow:
        {_format_workflow_steps(auto_workflow['steps'])}

        You can execute this workflow automatically, or modify it based on context.
        """
```

---

## 📊 Workflow Analytics Dashboard

**Create `memory/workflow_analyzer.py`:**

```python
#!/usr/bin/env python3
"""
Analyze workflow patterns and suggest optimizations
"""
from memory import store
from collections import Counter, defaultdict

def analyze_workflows():
    """Generate workflow analytics"""

    # Load all workflows
    workflows = [
        e["data"] for e in store._load_jsonl(store.EVENTS_PATH)
        if e.get("kind") == "workflow"
    ]

    # 1. Most common workflows
    intents = Counter(wf["intent"] for wf in workflows)
    print("=== Most Common Workflows ===")
    for intent, count in intents.most_common(10):
        print(f"{count:3d}x {intent}")

    # 2. Success rates
    print("\n=== Success Rates by Workflow ===")
    by_intent = defaultdict(list)
    for wf in workflows:
        by_intent[wf["intent"]].append(wf["success"])

    for intent, successes in sorted(by_intent.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        success_rate = sum(successes) / len(successes)
        print(f"{success_rate:5.1%} ({len(successes):2d} runs) - {intent}")

    # 3. Slowest workflows
    print("\n=== Slowest Workflows ===")
    sorted_by_duration = sorted(workflows, key=lambda w: w["duration"], reverse=True)
    for wf in sorted_by_duration[:10]:
        print(f"{wf['duration']:6.1f}s - {wf['intent']}")

    # 4. Most common command sequences
    print("\n=== Most Common Command Sequences ===")
    sequences = []
    for wf in workflows:
        seq = tuple(step["operation"] for step in wf["steps"])
        sequences.append(seq)

    seq_counts = Counter(sequences)
    for seq, count in seq_counts.most_common(10):
        if count > 1:  # Only show repeated patterns
            print(f"{count:3d}x {' → '.join(seq)}")

    # 5. Automation candidates
    print("\n=== Automation Candidates ===")
    candidates = []
    for intent, successes in by_intent.items():
        if len(successes) >= 5 and sum(successes) / len(successes) > 0.9:
            candidates.append((len(successes), intent))

    for count, intent in sorted(candidates, reverse=True)[:5]:
        print(f"{count:3d} successful runs - {intent}")
        print("    → Consider creating a workflow shortcut")

if __name__ == "__main__":
    analyze_workflows()
```

**Run it:**
```bash
python3 /Users/patricksomerville/Desktop/Trapdoor/memory/workflow_analyzer.py
```

---

## 🚀 Practical Workflow Patterns to Capture

### Pattern 1: Project Status Check

```python
# After 3+ successful executions, Qwen learns:
WORKFLOW["check project"] = {
    "steps": [
        {"op": "fs_ls", "path": "{project_dir}"},
        {"op": "fs_read", "path": "{project_dir}/package.json"},
        {"op": "exec", "cmd": ["git", "status"]},
        {"op": "exec", "cmd": ["npm", "test"]},
    ],
    "confidence": 0.95,
    "success_rate": 1.0,
    "avg_duration": 5.2
}

# Next time user says "check project", Qwen auto-suggests or auto-executes
```

### Pattern 2: Deploy Workflow

```python
WORKFLOW["deploy to staging"] = {
    "steps": [
        {"op": "exec", "cmd": ["git", "pull"]},
        {"op": "exec", "cmd": ["npm", "run", "build"]},
        {"op": "exec", "cmd": ["npm", "test"]},
        {"op": "exec", "cmd": ["rsync", "-av", "dist/", "staging:/var/www/"]},
    ],
    "requires_confirmation": True,  # Learned: user always reviews before deploy
    "error_recovery": {
        "npm test fails": ["npm", "install", "&&", "npm", "test"]
    }
}
```

### Pattern 3: Research Pattern

```python
WORKFLOW["research {topic}"] = {
    "steps": [
        {"op": "web_fetch", "url": "https://scholar.google.com/scholar?q={topic}"},
        {"op": "fs_write", "path": "/tmp/research.txt", "content": "{results}"},
        {"op": "delegate", "model": "gpt4", "task": "summarize research"},
    ],
    "learned": "User prefers GPT-4 for research summarization"
}
```

### Pattern 4: Code Review Pattern

```python
WORKFLOW["review {file}"] = {
    "steps": [
        {"op": "fs_read", "path": "{file}"},
        {"op": "exec", "cmd": ["git", "blame", "{file}"]},
        {"op": "delegate", "model": "gpt4", "task": "security review"},
        {"op": "fs_write", "path": "{file}.review.md", "content": "{analysis}"},
    ],
    "learned": "User wants security reviews saved as .review.md files"
}
```

---

## 🎯 Quick Start Implementation

### Step 1: Enhance Event Logging (Today, 30 minutes)

```bash
# Backup current memory
cp memory/store.py memory/store.py.backup

# Add workflow tracking functions to store.py
# (See Phase 1 code above)
```

### Step 2: Add Workflow Context to Chat (Today, 1 hour)

```bash
# Modify local_agent_server.py to track workflows
# Add _start_workflow_tracking, _add_workflow_step, _complete_workflow
# (See Phase 2 code above)
```

### Step 3: Analyze Current Usage (Right Now)

```bash
# See what patterns already exist
python3 << 'EOF'
from memory import store
import json

events = list(store._load_jsonl(store.EVENTS_PATH))
print(f"Total events: {len(events)}")

# Show event types
from collections import Counter
event_types = Counter(e.get("kind") for e in events)
print("\nEvent types:")
for kind, count in event_types.most_common():
    print(f"  {kind}: {count}")

# Show recent operations
print("\nRecent operations:")
for e in events[-10:]:
    print(f"  {e['kind']}: {e['data'].get('summary', '')[:60]}")
EOF
```

### Step 4: Create Workflow Analyzer (Today, 30 minutes)

```bash
# Create the analyzer script
# (See workflow_analyzer.py code above)

# Run it to see current patterns
python3 memory/workflow_analyzer.py
```

---

## 📈 Expected Results

### Week 1
- ✅ All workflows captured with full context
- ✅ Workflow analyzer shows top patterns
- ✅ Identify 3-5 automation candidates

### Week 2
- ✅ Qwen suggests past workflows for similar requests
- ✅ Success rates tracked per workflow
- ✅ Error recovery patterns identified

### Week 3
- ✅ Auto-execution for high-confidence workflows
- ✅ Workflow shortcuts ("deploy" → full deploy sequence)
- ✅ Continuous optimization from real usage

### Week 4
- ✅ 50%+ reduction in repeated multi-step commands
- ✅ Automatic error recovery
- ✅ Personalized workflow library

---

## 💡 Advanced: Workflow Refinement Loop

```python
class WorkflowRefiner:
    """Continuously improve workflows based on usage"""

    def analyze_workflow_efficiency(self, workflow_id: str):
        """Find bottlenecks and optimization opportunities"""
        executions = self.get_workflow_executions(workflow_id)

        # Find slow steps
        step_durations = defaultdict(list)
        for exec in executions:
            for step in exec["steps"]:
                step_durations[step["operation"]].append(step.get("duration", 0))

        # Suggest optimizations
        optimizations = []
        for op, durations in step_durations.items():
            avg_duration = sum(durations) / len(durations)
            if avg_duration > 5.0:  # Steps taking >5s
                optimizations.append({
                    "step": op,
                    "avg_duration": avg_duration,
                    "suggestion": self._suggest_optimization(op, avg_duration)
                })

        return optimizations

    def _suggest_optimization(self, operation: str, duration: float) -> str:
        """Suggest ways to speed up slow operations"""
        if operation == "exec" and "npm test" in operation:
            return "Consider running tests in parallel or caching dependencies"
        elif operation == "fs_read" and duration > 2.0:
            return "Large file - consider streaming or partial reads"
        elif "api_call" in operation:
            return "Consider caching API responses"
        return "Monitor for performance improvements"
```

---

## 🎬 Real Example from Your Usage

Based on your existing 35 events, you already have patterns. Let's extract them:

```bash
python3 << 'EOF'
from memory import store

events = list(store._load_jsonl(store.EVENTS_PATH))

# Find command sequences
sequences = []
current_seq = []

for e in events:
    if e["kind"] in ["fs_read", "fs_ls", "exec"]:
        current_seq.append(e["kind"])
        if len(current_seq) >= 3:
            sequences.append(tuple(current_seq[-3:]))

from collections import Counter
seq_counts = Counter(sequences)

print("Common 3-step patterns in your usage:")
for seq, count in seq_counts.most_common(5):
    if count > 1:
        print(f"{count}x: {' → '.join(seq)}")
EOF
```

This will show you what workflows you're already repeating that could be automated!

---

**Let's capture your real workflows and make them smarter** 🚀

