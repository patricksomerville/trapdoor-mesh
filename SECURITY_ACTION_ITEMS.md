# Trapdoor Security - Immediate Action Items

**Date:** 2025-10-28
**Status:** 🔴 CRITICAL VULNERABILITIES IDENTIFIED

---

## ⚠️ DO NOT DEPLOY TO PRODUCTION

Critical security issues must be resolved before production use.

---

## 🚨 CRITICAL - Fix Within 24 Hours

### 1. Compromised Production Token
**File:** `trapdoor_connector.py` lines 29-31

**Action Required:**
```bash
# 1. Immediately revoke the exposed token
python3 -c "
from security import TokenManager
tm = TokenManager()
tm.disable_token('migrated_1')
tm.save_tokens()
print('Token disabled')
"

# 2. Remove hardcoded credentials
git rm trapdoor_connector.py
# Create trapdoor_connector_template.py instead

# 3. Rotate ALL tokens (assume compromise)
./control_panel.py
# Select option 4: Rotate tools token

# 4. Check Git history
git log --all --full-history -- "*connector*"
# All tokens in history are compromised - rotate them
```

**Create secure connector template:**
```python
# trapdoor_connector_template.py
import os

BASE_URL = os.getenv("TRAPDOOR_URL")
TOKEN = os.getenv("TRAPDOOR_TOKEN")

if not BASE_URL or not TOKEN:
    raise ValueError("""
    Set environment variables:
      export TRAPDOOR_URL='https://your-url.ngrok-free.dev'
      export TRAPDOOR_TOKEN='your-token-here'
    """)
```

---

## 🔴 HIGH PRIORITY - Fix Within 7 Days

### 2. CORS Misconfiguration
**File:** `chatgpt_proxy.py` line 31

**Current (INSECURE):**
```python
CORS(app)  # Allow requests from any origin
```

**Fixed:**
```python
CORS(app, origins=[
    "http://localhost:3000",
    # Add specific allowed origins only
])

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response
```

### 3. Path Traversal Prevention
**File:** `security.py` method `_check_path_allowed()`

**Add strict path validation:**
```python
def _check_path_allowed(self, token_info: TokenInfo, path: Path) -> bool:
    try:
        # Resolve path strictly (must exist)
        path_resolved = path.expanduser().resolve(strict=True)
        path_str = str(path_resolved)

        # Prevent directory traversal
        if ".." in path.parts:
            return False

        # Get real path (resolve symlinks)
        path_real = str(path_resolved.resolve())

    except (OSError, RuntimeError):
        return False  # Invalid path

    # Check against denylists with BOTH resolved and real paths
    for denied in self.global_denylist:
        denied_real = str(Path(denied).expanduser().resolve())
        if path_str.startswith(denied_real) or path_real.startswith(denied_real):
            return False

    # Check allowlist
    if token_info.path_allowlist:
        for allowed in token_info.path_allowlist:
            allowed_real = str(Path(allowed).expanduser().resolve())
            if path_str.startswith(allowed_real) or path_real.startswith(allowed_real):
                return True
        return False

    return True
```

### 4. Approval Queue Race Condition
**File:** `security.py` class `ApprovalQueue`

**Replace polling with event notifications:**
```python
from threading import Event

class ApprovalQueue:
    def __init__(self):
        self.pending: Dict[str, PendingOperation] = {}
        self.lock = threading.RLock()
        self.events: Dict[str, Event] = {}

    def request_approval(self, operation: str, details: Dict[str, Any]) -> str:
        request_id = secrets.token_hex(16)  # Increased from 8

        with self.lock:
            event = Event()
            self.events[request_id] = event
            self.pending[request_id] = PendingOperation(
                request_id=request_id,
                operation=operation,
                details=details,
                timestamp=time.time(),
                status="pending"
            )

        return request_id

    def check_approval(self, request_id: str, timeout: int = 30) -> bool:
        with self.lock:
            if request_id not in self.events:
                return False
            event = self.events[request_id]

        # Wait for notification (not polling)
        if not event.wait(timeout=timeout):
            with self.lock:
                self.pending.pop(request_id, None)
                self.events.pop(request_id, None)
            return False

        with self.lock:
            op = self.pending.get(request_id)
            approved = op and op.status == "approved"
            self.pending.pop(request_id, None)
            self.events.pop(request_id, None)
            return approved

    def approve(self, request_id: str) -> bool:
        with self.lock:
            if request_id in self.pending:
                self.pending[request_id].status = "approved"
                if request_id in self.events:
                    self.events[request_id].set()
                return True
        return False
```

---

## 🟡 MEDIUM PRIORITY - Fix Within 30 Days

### 5. Input Validation
Add Pydantic models to all FastAPI endpoints:
```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)

    @validator('prompt')
    def no_null_bytes(cls, v):
        if '\x00' in v:
            raise ValueError('Null bytes not allowed')
        return v
```

### 6. Secure Logging
Replace print statements with proper logging:
```python
import logging

logger = logging.getLogger("trapdoor.security")

# Redact sensitive data
class TokenRedactingFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r'Bearer [a-f0-9]{32}', 'Bearer [REDACTED]', str(record.msg))
        return True

logger.addFilter(TokenRedactingFilter())
```

### 7. Token Cleanup
Add periodic cleanup of expired tokens:
```python
def cleanup_expired_tokens(self) -> int:
    now = datetime.now()
    removed = 0

    with self.lock:
        expired_ids = [
            tid for tid, tinfo in self.tokens.items()
            if tinfo.expires and tinfo.expires < now
        ]

        for tid in expired_ids:
            token_value = self.tokens[tid].token
            del self.tokens[tid]
            del self.token_lookup[token_value]
            removed += 1

        if removed > 0:
            self.save_tokens()

    return removed
```

---

## 🔍 Verification Tests

After fixes, run these tests:

```bash
# Test 1: Verify compromised token is disabled
curl -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a" \
  http://localhost:8080/health
# Expected: 403 or 401

# Test 2: Path traversal blocked
curl -H "Authorization: Bearer NEW_TOKEN" \
  "http://localhost:8080/fs/read?path=/tmp/../../../etc/passwd"
# Expected: 403 Permission denied

# Test 3: CORS restrictions
curl -H "Origin: https://evil.com" \
  -H "Authorization: Bearer NEW_TOKEN" \
  http://localhost:5001/health
# Expected: CORS error or no Access-Control-Allow-Origin header

# Test 4: Oversized request blocked
dd if=/dev/zero bs=1M count=10 | \
  curl -X POST -H "Content-Type: application/json" \
  --data-binary @- http://localhost:5001/chat
# Expected: 413 Request too large
```

---

## 📋 Checklist

- [ ] Disable compromised token `90ac04027a0b4aba685dcae29eeed91a`
- [ ] Remove `trapdoor_connector.py` from Git
- [ ] Create secure connector template with env vars
- [ ] Rotate all production tokens
- [ ] Fix CORS configuration
- [ ] Add security headers
- [ ] Implement strict path validation
- [ ] Fix approval queue race condition
- [ ] Add input validation to all endpoints
- [ ] Replace debug prints with secure logging
- [ ] Add token cleanup mechanism
- [ ] Run verification tests
- [ ] Update documentation with new security practices

---

## 📚 Next Steps

1. **Immediate:** Fix Critical issues (token exposure)
2. **Week 1:** Fix High issues (CORS, path traversal, race conditions)
3. **Week 2-4:** Fix Medium issues (validation, logging, cleanup)
4. **Month 2:** Add security testing suite
5. **Month 3:** External security audit

---

## 📞 Support

If you need help with any of these fixes:
1. Check full audit report: `SECURITY_AUDIT_REPORT.md`
2. Each finding has detailed remediation code
3. Test each fix before deploying

---

**Remember:** Security is not optional. These fixes protect YOUR system from unauthorized access, data loss, and potential compromise. Don't skip them.
