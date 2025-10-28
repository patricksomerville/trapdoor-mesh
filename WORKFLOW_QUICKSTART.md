# Workflow Learning System - Quick Start

**Created:** October 28, 2025
**Status:** Phase 1 Complete - Ready for Integration
**Goal:** Use every Qwen interaction as learning material for smarter workflows

---

## ✅ What's Done

### 1. Core System (memory/store.py)
- ✅ `record_workflow_event()` - Records complete workflows
- ✅ `find_similar_workflows()` - Finds past similar workflows
- ✅ `get_workflow_stats()` - Success rates and metrics
- ✅ `format_workflow_suggestions()` - Formats suggestions for Qwen
- ✅ `_extract_workflow_tags()` - Auto-tags workflows

**Test Status:** All functions working correctly ✓

### 2. Analysis Tool (memory/workflow_analyzer.py)
- ✅ Event type distribution
- ✅ Common command sequences
- ✅ Most accessed paths
- ✅ Automation candidate identification
- ✅ Activity timeline analysis

**Test Status:** Working, analyzed 38 existing events ✓

### 3. Documentation
- ✅ `WORKFLOW_LEARNING_SYSTEM.md` - Complete design (35KB)
- ✅ `WORKFLOW_INTEGRATION_GUIDE.md` - Integration instructions (NEW)
- ✅ `IMPLEMENTATION_SUMMARY.md` - Overall roadmap
- ✅ `QWEN_INTERNET_CAPABILITIES.md` - Updated with 2025 models
- ✅ `MEMORY_ENHANCEMENT_ANALYSIS.md` - Semantic search roadmap

---

## 🎯 What You Can Do Right Now

### Check Current Patterns

```bash
cd /Users/patricksomerville/Desktop/Trapdoor
python3 memory/workflow_analyzer.py
```

This shows you what workflows you're already repeating!

### Test the System

```python
# Quick test script
cd /Users/patricksomerville/Desktop/Trapdoor
python3 << 'EOF'
from memory import store
import time

# Record a test workflow
intent = "Test workflow tracking"
steps = [
    {"operation": "test_step_1", "detail": "first step"},
    {"operation": "test_step_2", "detail": "second step"}
]
result = "Test completed successfully"

store.record_workflow_event(
    intent=intent,
    steps=steps,
    result=result,
    success=True,
    duration=1.5
)

print("✓ Test workflow recorded")

# Verify it
workflows = [e["data"] for e in store._load_jsonl(store.EVENTS_PATH)
             if e.get("kind") == "workflow"]
print(f"✓ Total workflows: {len(workflows)}")

# Find similar
similar = store.find_similar_workflows("test", limit=2)
print(f"✓ Similar workflows found: {len(similar)}")
EOF
```

---

## 📋 Next Steps (In Order)

### Step 1: Integrate Into Your Server (1-2 hours)

**Find your main OpenAI-compatible server file** (the one that handles chat completions)

**Follow:** `WORKFLOW_INTEGRATION_GUIDE.md`

**Key Changes:**
1. Import the workflow tracking module
2. Wrap your chat endpoint with `WorkflowTracker`
3. Call `tracker.add_step()` for each operation
4. Let it automatically record when done

**Example Pattern:**
```python
with WorkflowTracker(user_intent) as tracker:
    # Your existing chat logic
    tracker.add_step("filesystem", {"op": "read", "path": path})
    tracker.add_step("command", {"cmd": cmd})
    # Result is recorded automatically
```

### Step 2: Use Normally (3-7 days)

Just use Trapdoor as you normally would!

- Every request is now a learning opportunity
- Check progress daily: `python3 memory/workflow_analyzer.py`
- Watch patterns emerge

**Goal:** 50-100 real workflows recorded

### Step 3: Enable Suggestions (30 minutes)

Once you have data, add workflow suggestions to chat:

```python
# Before processing chat
suggestions = store.find_similar_workflows(user_intent, limit=3)
if suggestions:
    hints = store.format_workflow_suggestions(suggestions)
    # Add hints to system message or inject into context
```

**Goal:** Qwen sees past successful patterns

### Step 4: Monitor & Optimize (Ongoing)

Create simple monitoring:

```bash
# Add to crontab or run weekly
cd /Users/patricksomerville/Desktop/Trapdoor
python3 memory/workflow_analyzer.py > weekly_analysis_$(date +%Y%m%d).txt
```

Watch for:
- Repeated patterns (automation candidates)
- High-success workflows (teach Qwen these)
- Failed workflows (improve error handling)

---

## 📊 Success Criteria

### Week 1
- [ ] 50+ workflows recorded
- [ ] 3-5 repeated patterns identified
- [ ] Analyzer shows meaningful patterns

### Week 2
- [ ] 100+ workflows recorded
- [ ] Suggestions integrated into chat
- [ ] Qwen referencing past workflows

### Month 1
- [ ] 500+ workflows recorded
- [ ] 10+ common workflows recognized
- [ ] 30% reduction in repeated steps
- [ ] Auto-suggestions for high-confidence workflows

---

## 🐛 Troubleshooting

### "No workflows being recorded"

```python
# Check if workflow tracking is working
from memory import store
import time

store.record_workflow_event(
    intent="debug test",
    steps=[{"op": "test"}],
    result="test",
    success=True,
    duration=0.1
)

workflows = [e for e in store._load_jsonl(store.EVENTS_PATH)
             if e.get("kind") == "workflow"]
print(f"Workflows in database: {len(workflows)}")
```

### "Analyzer shows no patterns"

Need more data! Use the system naturally for a few days.

### "Suggestions not appearing"

1. Check that you have 5+ workflows
2. Verify similarity matching is working:

```python
from memory import store
similar = store.find_similar_workflows("list files", limit=3)
print(f"Found {len(similar)} similar workflows")
```

---

## 🎓 Learning Resources

1. **Start Here:** `WORKFLOW_INTEGRATION_GUIDE.md` - How to integrate
2. **Deep Dive:** `WORKFLOW_LEARNING_SYSTEM.md` - Full design and theory
3. **Big Picture:** `IMPLEMENTATION_SUMMARY.md` - Overall roadmap
4. **Latest Models:** `QWEN_INTERNET_CAPABILITIES.md` - GPT-5, Sonnet 4.5, Gemini 2.5
5. **Future:** `MEMORY_ENHANCEMENT_ANALYSIS.md` - Semantic search upgrade

---

## 🚀 The Vision

**Today:**
```
User: "Check project status"
Qwen: [executes commands manually]
```

**After Learning:**
```
User: "Check project status"
Qwen: "I recognize this! You've done this 5 times before.
       Standard workflow:
       1. git status
       2. npm test
       3. Check for uncommitted changes

       Success rate: 100%

       Running workflow..."
```

**Result:** Qwen gets smarter with every interaction!

---

## 💡 Key Insights

1. **Real > Theoretical** - Learn from actual usage, not hypothetical workflows
2. **Progressive** - System gets better over time automatically
3. **No Training Required** - Just use it normally
4. **Pattern Recognition** - Similar requests = Similar solutions
5. **Compounding Returns** - Each workflow makes future requests faster

---

## 📞 Quick Reference

```bash
# Analyze patterns
python3 memory/workflow_analyzer.py

# Test workflow functions
python3 -c "from memory import store; store.record_workflow_event('test', [], 'ok', True, 1.0)"

# Check stats
python3 -c "from memory import store; print(store.get_workflow_stats())"

# Find similar workflows
python3 -c "from memory import store; print(store.find_similar_workflows('list files'))"
```

---

**Ready to start? Open `WORKFLOW_INTEGRATION_GUIDE.md` and add workflow tracking to your server!** 🎯

The system is ready. Every interaction from now on makes Qwen smarter. Just integrate, use normally, and watch it learn! 🚀
