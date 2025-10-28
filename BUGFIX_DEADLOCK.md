# Deadlock Bug Fix - 2025-10-28

## Problem

Token management endpoints (`/tokens/list`, `/approval/pending`) were timing out after ~5 seconds with no response.

## Root Cause

**Nested lock deadlock in `security.py`:**

The `TokenManager.validate_token()` method was calling `save_tokens()` while holding a lock:

```python
def validate_token(self, token: str) -> TokenInfo:
    ...
    with self.lock:  # Acquires lock
        token_info.last_used = datetime.now()
        self.save_tokens()  # Tries to acquire SAME lock again -> DEADLOCK

def save_tokens(self) -> None:
    with self.lock:  # Can't acquire - already held!
        ...
```

Python's `threading.Lock()` is **not reentrant** - a thread cannot acquire the same lock twice. This caused validate_token() to hang forever waiting for a lock it already owns.

## Solution

Changed all `threading.Lock()` to `threading.RLock()` (reentrant lock) in three places:

1. `TokenManager.__init__()` (line 151)
2. `RateLimiter.__init__()` (line 407)
3. `ApprovalQueue.__init__()` (line 498)

```python
# Before
self.lock = threading.Lock()

# After
self.lock = threading.RLock()
```

`RLock` allows the same thread to acquire the lock multiple times (as long as it releases it the same number of times).

## Files Modified

- `/Users/patricksomerville/Desktop/Trapdoor/security.py` - Changed 3 Lock() to RLock()

## Testing

All endpoints now respond correctly:

```
✅ /health - 200 OK
✅ /tokens/list - 200 OK (previously timeout)
✅ /approval/pending - 200 OK (previously timeout)
✅ /fs/ls - 200 OK
```

Response time: < 100ms (previously timeout after 5+ seconds)

## Why This Wasn't Caught Earlier

1. The endpoints were only added in the recent security enhancement
2. Simple auth operations (like `/fs/ls`) don't call `save_tokens()` on every request
3. Token management endpoints were the first to hit the validate → save → validate pattern
4. The debug logging we added never appeared because the code never reached the handler

## Lessons

- Always use `RLock` when locks might be acquired recursively
- Test new endpoints immediately after integration
- Timeouts without errors = check for deadlocks
- Add timeout monitoring to catch hangs early

## Status

**✅ FIXED** - All endpoints operational as of 2025-10-28 11:54 AM

---

**Impact:** High (blocked all token management functionality)
**Severity:** Critical (complete hang, no error message)
**Fix Complexity:** Trivial (one-word change × 3)
**Time to Fix:** ~1 hour (debugging took most of the time)
