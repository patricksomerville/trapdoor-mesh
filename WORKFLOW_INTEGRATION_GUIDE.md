# Workflow Learning Integration Guide

**Purpose:** Add workflow tracking to any OpenAI-compatible server to enable Qwen to learn from real interactions.

**Target:** Any server implementing OpenAI-compatible endpoints (Flask, FastAPI, Express, etc.)

---

## Core Concept

Workflow learning captures:
1. **Intent** - What the user asked for
2. **Steps** - All operations executed (filesystem, commands, API calls)
3. **Result** - The final outcome
4. **Success** - Did it work?
5. **Duration** - How long it took

Over time, Qwen learns to recognize similar requests and suggests proven workflows.

---

## Integration Architecture

```
User Request
    ↓
[Track Intent + Start Timer]
    ↓
Execute Operations
    ↓
[Track Each Step]
    ↓
Generate Response
    ↓
[Record Complete Workflow]
    ↓
Return to User
```

---

## Implementation Steps

### Step 1: Import Workflow Tracking

At the top of your server file:

```python
import sys
import time
from pathlib import Path

# Add memory module to path
sys.path.insert(0, str(Path(__file__).parent / "memory"))
from memory import store
```

### Step 2: Create Workflow Context Manager

Add this helper class to automatically track workflows:

```python
class WorkflowTracker:
    """Context manager for tracking multi-step workflows"""

    def __init__(self, intent: str):
        self.intent = intent
        self.steps = []
        self.start_time = time.time()
        self.success = True
        self.result = ""

    def add_step(self, operation: str, details: dict):
        """Record a single step in the workflow"""
        self.steps.append({
            "operation": operation,
            "timestamp": time.time(),
            **details
        })

    def set_result(self, result: str, success: bool = True):
        """Set the final result and success status"""
        self.result = result
        self.success = success

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatically record workflow when exiting context"""
        duration = time.time() - self.start_time

        # On exception, mark as failed
        if exc_type is not None:
            self.success = False
            self.result = f"Error: {exc_type.__name__}: {exc_val}"

        # Record the complete workflow
        store.record_workflow_event(
            intent=self.intent,
            steps=self.steps,
            result=self.result,
            success=self.success,
            duration=duration
        )

        return False  # Don't suppress exceptions
```

### Step 3: Integrate Into Chat Endpoint

#### Flask Example:

```python
@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    data = request.json
    messages = data.get("messages", [])

    # Extract user intent (last user message)
    user_messages = [m for m in messages if m.get("role") == "user"]
    intent = user_messages[-1].get("content", "Unknown request") if user_messages else "Unknown"

    # Track this workflow
    with WorkflowTracker(intent) as tracker:
        # Process the chat completion
        response_text = ""

        try:
            # Your existing chat logic here
            # Example: call LLM, parse tool calls, execute operations

            # IMPORTANT: Track each step
            if "filesystem" in response_text.lower():
                tracker.add_step("fs_operation", {"type": "read", "path": "/some/path"})

            if "exec" in response_text.lower():
                tracker.add_step("command", {"cmd": ["ls", "-la"]})

            # Set final result
            tracker.set_result("Successfully completed request", success=True)

            return jsonify({
                "choices": [{
                    "message": {"role": "assistant", "content": response_text}
                }]
            })

        except Exception as e:
            tracker.set_result(f"Failed: {str(e)}", success=False)
            raise
```

#### FastAPI Example:

```python
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    # Extract user intent
    user_messages = [m for m in request.messages if m.role == "user"]
    intent = user_messages[-1].content if user_messages else "Unknown"

    # Track workflow
    with WorkflowTracker(intent) as tracker:
        # Your chat completion logic
        # Track each step as you go
        tracker.add_step("llm_call", {"model": request.model})

        # ... your logic ...

        tracker.set_result("Completed successfully")
        return ChatResponse(...)
```

### Step 4: Track Individual Operations

For filesystem and exec endpoints, add tracking:

```python
@app.route("/fs/ls", methods=["GET"])
def fs_list():
    path = request.args.get("path", "/")

    # Record this event (existing pattern)
    store.record_event("fs_ls", {"path": path})

    # ... existing logic ...

    return jsonify({"entries": entries})
```

```python
@app.route("/exec", methods=["POST"])
def exec_command():
    data = request.json
    cmd = data.get("cmd", [])

    # Record this event
    store.record_event("exec", {"cmd": cmd})

    # ... existing logic ...

    return jsonify({"stdout": stdout, "stderr": stderr})
```

---

## Enhanced Features

### Feature 1: Workflow Suggestions

Before executing a request, check for similar past workflows:

```python
def suggest_workflow(intent: str):
    """Find and suggest similar past workflows"""
    similar = store.find_similar_workflows(intent, limit=3)

    if similar:
        suggestions = store.format_workflow_suggestions(similar)
        # Inject suggestions into system prompt or return as hint
        return suggestions

    return None
```

Usage in chat endpoint:

```python
@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    # ... extract intent ...

    # Check for similar workflows
    suggestions = suggest_workflow(intent)

    if suggestions:
        # Add suggestions to system message
        messages.insert(0, {
            "role": "system",
            "content": f"Past experience:\n{suggestions}"
        })

    # ... proceed with normal logic ...
```

### Feature 2: Success Rate Monitoring

Add an endpoint to check workflow performance:

```python
@app.route("/workflow/stats", methods=["GET"])
def workflow_stats():
    intent = request.args.get("intent")
    stats = store.get_workflow_stats(intent)

    return jsonify({
        "total_workflows": stats["total"],
        "successful": stats["successful"],
        "failed": stats["failed"],
        "success_rate": f"{stats['success_rate']*100:.1f}%",
        "avg_duration": f"{stats['avg_duration']:.2f}s"
    })
```

### Feature 3: Workflow Dashboard Data

```python
@app.route("/workflow/recent", methods=["GET"])
def recent_workflows():
    limit = int(request.args.get("limit", 10))

    # Get recent workflow events
    events = store.get_recent_events(limit=limit*2)  # Get more than needed
    workflows = [
        e["data"] for e in events
        if e.get("kind") == "workflow"
    ][:limit]

    return jsonify({
        "workflows": workflows,
        "total": len(workflows)
    })
```

---

## Testing the Integration

### Test 1: Basic Workflow Recording

```python
# Test script: test_workflow_tracking.py

from memory import store
import time

# Simulate a workflow
intent = "List files in home directory"

# Manual tracking example
start = time.time()
steps = [
    {"operation": "fs_ls", "path": "/Users/patricksomerville"},
    {"operation": "format_results", "count": 15}
]
result = "Found 15 files"
success = True
duration = time.time() - start

store.record_workflow_event(intent, steps, result, success, duration)
print("✓ Workflow recorded")

# Verify it was saved
workflows = [e["data"] for e in store._load_jsonl(store.EVENTS_PATH)
             if e.get("kind") == "workflow"]
print(f"✓ Total workflows: {len(workflows)}")
```

### Test 2: Similarity Matching

```python
# Find similar workflows
similar = store.find_similar_workflows("Show files in desktop", limit=3)

if similar:
    print(f"✓ Found {len(similar)} similar workflows")
    for wf in similar:
        print(f"  - {wf['intent'][:60]} ({wf['step_count']} steps)")
else:
    print("✗ No similar workflows found")
```

### Test 3: Statistics

```python
stats = store.get_workflow_stats()
print(f"✓ Workflow Statistics:")
print(f"  Total: {stats['total']}")
print(f"  Success rate: {stats['success_rate']*100:.1f}%")
print(f"  Avg duration: {stats['avg_duration']:.2f}s")
```

---

## Gradual Rollout Plan

### Phase 1: Passive Recording (Week 1)
- Add WorkflowTracker to main endpoints
- Record all workflows silently
- No changes to user experience
- **Goal:** Capture 50-100 real workflows

### Phase 2: Analysis & Tuning (Week 2)
- Run workflow_analyzer.py daily
- Identify most common patterns
- Fine-tune similarity matching
- **Goal:** Understand usage patterns

### Phase 3: Suggestions (Week 3)
- Enable workflow suggestions
- Show past successful patterns to Qwen
- Still let Qwen decide execution
- **Goal:** Improve Qwen's awareness

### Phase 4: Auto-Execution (Week 4+)
- For high-confidence workflows (90%+ success)
- Auto-suggest or auto-execute common patterns
- **Goal:** Reduce repetitive work by 50%

---

## Monitoring & Maintenance

### Daily Health Check

Create `scripts/check_workflows.sh`:

```bash
#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Workflow Health Check ==="
python3 << 'EOF'
from memory import store

events = list(store._load_jsonl(store.EVENTS_PATH))
workflows = [e["data"] for e in events if e.get("kind") == "workflow"]

if not workflows:
    print("⚠️  No workflows recorded yet")
    exit(0)

total = len(workflows)
successful = sum(1 for w in workflows if w.get("success"))
failed = total - successful

print(f"✓ Total workflows: {total}")
print(f"✓ Successful: {successful} ({successful/total*100:.1f}%)")
print(f"✓ Failed: {failed} ({failed/total*100:.1f}%)")

# Recent activity
import time
recent_cutoff = time.time() - (24 * 3600)  # Last 24 hours
recent = [w for w in workflows if w.get("ts", 0) > recent_cutoff]
print(f"✓ Last 24h: {len(recent)} workflows")

if len(recent) == 0:
    print("⚠️  No recent workflow activity")
EOF
```

### Weekly Analysis

```bash
#!/bin/bash
# scripts/weekly_workflow_analysis.sh

cd "$(dirname "$0")/.."

echo "=== Weekly Workflow Analysis ==="
echo "Running analyzer..."
python3 memory/workflow_analyzer.py > workflow_analysis_$(date +%Y%m%d).txt

echo ""
echo "✓ Analysis saved to workflow_analysis_$(date +%Y%m%d).txt"
echo ""
echo "Top automation candidates:"
grep -A 5 "Potential Automation" workflow_analysis_$(date +%Y%m%d).txt
```

---

## Troubleshooting

### Problem: Workflows Not Being Recorded

**Check:**
1. Is memory/store.py imported correctly?
2. Does the memory/ directory exist?
3. Are there any import errors in logs?
4. Is the WorkflowTracker being used?

**Debug:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In WorkflowTracker.__exit__
print(f"Recording workflow: intent={self.intent}, steps={len(self.steps)}")
store.record_workflow_event(...)
print("✓ Workflow recorded")
```

### Problem: No Similar Workflows Found

**Check:**
1. Are there enough workflows in the database? (Need 5+)
2. Is the similarity threshold too high?
3. Are intents being captured correctly?

**Debug:**
```python
# Test similarity directly
from memory import store

all_workflows = [e["data"] for e in store._load_jsonl(store.EVENTS_PATH)
                 if e.get("kind") == "workflow"]
print(f"Total workflows: {len(all_workflows)}")

for wf in all_workflows[:5]:
    print(f"- {wf['intent'][:60]}")
```

### Problem: Steps Not Being Tracked

**Check:**
1. Is `tracker.add_step()` being called?
2. Are the operations actually executing?

**Debug:**
```python
# Add verbose logging to WorkflowTracker
def add_step(self, operation: str, details: dict):
    print(f"[STEP] {operation}: {details}")
    self.steps.append(...)
```

---

## Next Steps

1. **Implement Basic Tracking (1 hour)**
   - Add WorkflowTracker to main chat endpoint
   - Test with a few manual requests

2. **Verify Data Collection (1 day)**
   - Use system normally for a day
   - Run analyzer to see patterns

3. **Enable Suggestions (1 hour)**
   - Add workflow suggestion logic
   - Test that Qwen sees past patterns

4. **Monitor & Optimize (Ongoing)**
   - Run weekly analysis
   - Adjust similarity thresholds
   - Identify automation candidates

---

## Success Metrics

After 2 weeks:
- ✓ 100+ workflows recorded
- ✓ 5+ repeated patterns identified
- ✓ Suggestions appearing in responses
- ✓ 70%+ workflow success rate

After 1 month:
- ✓ 500+ workflows recorded
- ✓ 20+ common workflows recognized
- ✓ 30% reduction in repeated steps
- ✓ Auto-execution for high-confidence workflows

---

## Resources

- **workflow_analyzer.py** - Analyze existing patterns
- **memory/store.py** - Workflow tracking functions
- **WORKFLOW_LEARNING_SYSTEM.md** - Full design document
- **IMPLEMENTATION_SUMMARY.md** - Overall roadmap

**Support:** Check logs in `.proxy_runtime/` for server output

---

**Remember:** The goal is learning from REAL usage, not theoretical workflows. Start simple, let it capture actual interactions, then optimize based on what you discover! 🚀
