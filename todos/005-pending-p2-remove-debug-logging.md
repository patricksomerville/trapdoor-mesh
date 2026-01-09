---
status: pending
priority: p2
issue_id: "005"
tags: [code-quality, logging, cleanup, code-review]
dependencies: []
---

# Remove Debug Logging from Production Endpoints

## Problem Statement

Approval endpoints contain 6 debug `print()` statements that were added during deadlock debugging. These clutter production logs and should be removed or converted to proper logging.

## Findings

- **Discovered during:** Code pattern analysis by pattern-recognition-specialist agent
- **Location:** `approval_endpoints.py:92-120`
- **Count:** 6 debug print statements
- **Context:** Added during BUGFIX_DEADLOCK.md investigation

**Current Code:**
```python
@app.get("/tokens/list")
def list_tokens(authorization: Optional[str] = Header(None)):
    print("[DEBUG] /tokens/list called")      # ❌
    # ...
    print("[DEBUG] Extracting token")         # ❌
    print("[DEBUG] Validating token")         # ❌
    print("[DEBUG] Checking admin scope")     # ❌
    print(f"[DEBUG] Serializing {len(...)")   # ❌
    print("[DEBUG] Returning response")       # ❌
```

## Impact Assessment

**Severity:** 🟡 MODERATE (Code Quality)

**Issues:**
- Cluttered console output in production
- No log levels (can't disable debug)
- Inconsistent with rest of codebase
- Not production-ready
- Makes logs harder to parse

## Proposed Solutions

### Option 1: Remove Entirely (Recommended)
```python
@app.get("/tokens/list")
def list_tokens(authorization: Optional[str] = Header(None)):
    # Simply delete all print() statements
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")
    # ... rest of code ...
```

- **Pros**: Cleanest, simplest
- **Cons**: Lose debugging capability
- **Effort**: Trivial (5 minutes)
- **Risk**: None

### Option 2: Convert to Proper Logging
```python
import logging
logger = logging.getLogger(__name__)

@app.get("/tokens/list")
def list_tokens(authorization: Optional[str] = Header(None)):
    logger.debug("/tokens/list called")
    # ...
    logger.debug("Validating token")
    # ... etc
```

- **Pros**: Keeps debugging capability, proper log levels
- **Cons**: Slight complexity
- **Effort**: Small (15 minutes)
- **Risk**: None

## Recommended Action

**Option 1** (remove entirely)

**Why:**
- Debugging is complete (deadlock fixed)
- No ongoing need for this level of tracing
- Cleaner production logs
- Consistent with project philosophy (ship working code)

**If debugging needed again:** Use proper logging from the start.

## Technical Details

- **Affected Files**:
  - `/Users/patricksomerville/Desktop/Trapdoor/approval_endpoints.py` (lines 92-120)

- **Lines to Remove**:
  - Line 92: `print("[DEBUG] /tokens/list called")`
  - Line 99: `print("[DEBUG] Extracting token")`
  - Line 102: `print("[DEBUG] Validating token")`
  - Line 106: `print("[DEBUG] Checking admin scope")`
  - Line 109: `print(f"[DEBUG] Serializing {len(token_manager.tokens)} tokens")`
  - Line 120: `print("[DEBUG] Returning response")`

- **Related Components**: None

- **Database Changes**: No

## Acceptance Criteria

- [ ] All `[DEBUG]` print statements removed
- [ ] Code runs without console spam
- [ ] Endpoints still function correctly
- [ ] Code review completed

## Work Log

### 2025-10-28 - Code Review Discovery
**By:** pattern-recognition-specialist agent
**Actions:**
- Identified debug logging in production code
- Traced to deadlock debugging session
- Recommended cleanup

**Learnings:**
- Debug code should be removed after issue resolution
- Temporary logging should use proper logger with levels
- Production code should be clean

## Notes

**Context:** These were added in `BUGFIX_DEADLOCK.md` to trace where the timeout was occurring. Deadlock is now fixed (Lock → RLock), so debug logging no longer needed.

**Quick Win:** 5 minutes to clean, improves code quality immediately.

**Created:** 2025-10-28
