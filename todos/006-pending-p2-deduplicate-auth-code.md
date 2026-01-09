---
status: pending
priority: p2
issue_id: "006"
tags: [code-quality, refactoring, dry-principle, code-review]
dependencies: []
---

# Deduplicate Authentication Code Using FastAPI Dependencies

## Problem Statement

The same 5-line authorization block is copy-pasted across 6 different endpoints in `approval_endpoints.py`. This violates DRY principle and creates 30 lines of duplicated code that must be updated in 6 places for any change.

## Findings

- **Discovered during:** Code pattern analysis by pattern-recognition-specialist agent
- **Location:** `approval_endpoints.py` (6 endpoints)
- **Duplication count:** 6× (30 total lines)
- **Affected endpoints:**
  - `/tokens/list`
  - `/tokens/create`
  - `/tokens/rotate`
  - `/tokens/disable`
  - `/approval/pending`
  - `/approval/decide`

**Duplicated Code:**
```python
# Repeated in all 6 endpoints:
if not authorization or not authorization.startswith("Bearer "):
    raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")

token = authorization.split(" ", 1)[1]
token_info = token_manager.validate_token(token)

if "admin" not in token_info.scopes:
    raise HTTPException(status_code=403, detail="Admin scope required")
```

## Impact Assessment

**Severity:** 🟡 MODERATE (Code Quality)

**Issues:**
- **30 lines of duplication** across 6 endpoints
- Changes must be applied 6 times
- High risk of inconsistency (forget to update one)
- Violates DRY (Don't Repeat Yourself) principle
- Makes refactoring harder

**Example of Risk:**
If we want to change error messages or add logging, must update 6 locations.

## Proposed Solutions

### Option 1: FastAPI Dependency Injection (Recommended)
```python
from fastapi import Depends, Header, HTTPException

def require_admin_token(authorization: str = Header(...)) -> TokenInfo:
    """FastAPI dependency for admin authentication"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing/invalid Authorization header")

    token = authorization.split(" ", 1)[1]
    token_info = token_manager.validate_token(token)

    if "admin" not in token_info.scopes:
        raise HTTPException(403, "Admin scope required")

    return token_info

# Usage - replaces 5 lines with 1:
@app.get("/tokens/list")
def list_tokens(token_info: TokenInfo = Depends(require_admin_token)):
    """List all configured tokens"""
    tokens = []
    for tid, tinfo in token_manager.tokens.items():
        tokens.append({
            "token_id": tinfo.token_id,
            # ... rest of serialization
        })
    return {"tokens": tokens}
```

**Before (per endpoint):**
```python
def list_tokens(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):  # 1
        raise HTTPException(status_code=401, ...)                     # 2

    token = authorization.split(" ", 1)[1]                            # 3
    token_info = token_manager.validate_token(token)                  # 4

    if "admin" not in token_info.scopes:                              # 5
        raise HTTPException(status_code=403, ...)                     # 6
```

**After (per endpoint):**
```python
def list_tokens(token_info: TokenInfo = Depends(require_admin_token)):
    # 5 lines reduced to 1 parameter!
```

- **Pros**:
  - Eliminates 25 lines of duplication
  - Single source of truth for admin auth
  - Standard FastAPI pattern
  - Easier to test
  - Type-safe
- **Cons**:
  - Requires understanding FastAPI dependencies (minimal learning curve)
- **Effort**: Small (30 minutes)
- **Risk**: Low

### Option 2: Shared Helper Function
```python
def validate_admin_token(authorization: Optional[str]) -> TokenInfo:
    """Validate admin token from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing/invalid Authorization header")

    token = authorization.split(" ", 1)[1]
    token_info = token_manager.validate_token(token)

    if "admin" not in token_info.scopes:
        raise HTTPException(403, "Admin scope required")

    return token_info

# Usage:
@app.get("/tokens/list")
def list_tokens(authorization: Optional[str] = Header(None)):
    token_info = validate_admin_token(authorization)
    # ... rest of logic
```

- **Pros**: Simpler, no dependency injection
- **Cons**: Still need to call manually in each endpoint
- **Effort**: Small (20 minutes)
- **Risk**: Low

## Recommended Action

**Implement Option 1** (FastAPI dependency injection)

**Why:**
- More Pythonic and idiomatic FastAPI
- Cleaner endpoint signatures
- Automatic documentation in OpenAPI
- Type checking built-in
- Testable in isolation

**Implementation Steps:**

1. **Create dependency function:**
   ```python
   # At top of approval_endpoints.py
   from fastapi import Depends

   def require_admin_token(authorization: str = Header(...)) -> TokenInfo:
       """Require admin token for endpoint access"""
       if not authorization or not authorization.startswith("Bearer "):
           raise HTTPException(401, "Missing/invalid Authorization header")

       token = authorization.split(" ", 1)[1]
       token_info = token_manager.validate_token(token)

       if "admin" not in token_info.scopes:
           raise HTTPException(403, "Admin scope required")

       return token_info
   ```

2. **Update all 6 endpoints:**
   ```python
   # Before:
   def list_tokens(authorization: Optional[str] = Header(None)):
       if not authorization or not authorization.startswith("Bearer "):
           # ... 5 lines of auth ...

   # After:
   def list_tokens(token_info: TokenInfo = Depends(require_admin_token)):
       # Auth handled by dependency
   ```

3. **Test all endpoints still work**

4. **Update documentation** if needed

## Technical Details

- **Affected Files**:
  - `/Users/patricksomerville/Desktop/Trapdoor/approval_endpoints.py` (all 6 endpoints)

- **Endpoints to Update**:
  - `list_tokens()` (line ~85)
  - `create_token()` (line ~122)
  - `rotate_token()` (line ~144)
  - `disable_token()` (line ~166)
  - `list_pending_approvals()` (line ~15)
  - `decide_approval()` (line ~42)

- **Related Components**:
  - Token management API
  - Approval queue API

- **Database Changes**: No

- **LOC Impact**:
  - Before: ~173 lines
  - After: ~148 lines
  - **Reduction: 25 lines** (14%)

## Acceptance Criteria

- [ ] `require_admin_token()` dependency created
- [ ] All 6 endpoints updated to use dependency
- [ ] Duplicate auth code removed
- [ ] All endpoints tested and working
- [ ] OpenAPI docs updated automatically
- [ ] Code review completed

## Work Log

### 2025-10-28 - Code Review Discovery
**By:** pattern-recognition-specialist agent
**Actions:**
- Analyzed code patterns across codebase
- Identified authentication duplication
- Counted instances and calculated impact
- Recommended FastAPI dependency pattern

**Learnings:**
- Authentication is perfect use case for dependency injection
- FastAPI dependencies reduce boilerplate significantly
- Single source of truth prevents inconsistencies

## Notes

**Quick Win:** 30 minutes of work eliminates 25 lines of duplication.

**Bonus:** FastAPI dependencies are auto-documented in OpenAPI schema, so admin requirement will show up in API docs.

**Philosophy Alignment:**
"Build for yourself. Ship to yourself first."

This makes future changes easier for Patrick - change auth logic once instead of 6 times.

**Created:** 2025-10-28
**Source:** Code pattern analysis from comprehensive review
