# Secure Coding Guide for Trapdoor

Quick reference for developers working on Trapdoor. Keep this open while coding.

---

## 🚫 Never Do This

### 1. Hardcode Secrets
```python
# ❌ WRONG
TOKEN = "90ac04027a0b4aba685dcae29eeed91a"
API_KEY = "sk-1234567890"

# ✅ CORRECT
import os
TOKEN = os.getenv("TRAPDOOR_TOKEN")
if not TOKEN:
    raise ValueError("TRAPDOOR_TOKEN environment variable required")
```

### 2. Use `shell=True` in subprocess
```python
# ❌ WRONG - Command injection risk
subprocess.run(f"ls {user_input}", shell=True)

# ✅ CORRECT - Array form, no shell
subprocess.run(["ls", user_input], shell=False)
```

### 3. Trust User Input
```python
# ❌ WRONG - No validation
path = request.args.get('path')
with open(path, 'r') as f:
    return f.read()

# ✅ CORRECT - Validate first
path = Path(request.args.get('path', ''))
if not is_path_allowed(path):
    return jsonify({"error": "Path not allowed"}), 403
```

### 4. Log Sensitive Data
```python
# ❌ WRONG
logger.info(f"User logged in with token: {token}")
print(f"Password attempt: {password}")

# ✅ CORRECT
logger.info(f"User logged in with token: {token[:8]}...")
logger.info("Password authentication attempted")
```

### 5. Allow Unrestricted CORS
```python
# ❌ WRONG
CORS(app)  # Any origin

# ✅ CORRECT
CORS(app, origins=[
    "http://localhost:3000",
    "https://your-app.com"
])
```

---

## ✅ Always Do This

### 1. Validate All Input
```python
from pydantic import BaseModel, Field, validator

class UserInput(BaseModel):
    path: str = Field(..., min_length=1, max_length=4096)
    command: List[str] = Field(..., max_items=100)

    @validator('path')
    def validate_path(cls, v):
        # No null bytes
        if '\x00' in v:
            raise ValueError('Invalid path')
        # No traversal
        if '..' in Path(v).parts:
            raise ValueError('Path traversal not allowed')
        return v

    @validator('command')
    def validate_command(cls, v):
        # Check each arg
        for arg in v:
            if not isinstance(arg, str):
                raise ValueError('Command args must be strings')
            # No shell metacharacters
            if any(c in arg for c in [';', '&', '|', '`', '\n']):
                raise ValueError('Invalid characters in command')
        return v
```

### 2. Normalize Paths Before Checking
```python
def check_path_safe(path: Path, allowed_dirs: List[Path]) -> bool:
    try:
        # Expand ~ and resolve symlinks
        real_path = path.expanduser().resolve(strict=True)

        # Check against allowed directories
        for allowed_dir in allowed_dirs:
            allowed_real = allowed_dir.expanduser().resolve()
            if str(real_path).startswith(str(allowed_real)):
                return True

        return False

    except (OSError, RuntimeError):
        # Path doesn't exist or can't be accessed
        return False
```

### 3. Use Cryptographic Random for Security
```python
import secrets

# ✅ CORRECT - Cryptographically secure
token = secrets.token_hex(16)  # 32 characters
request_id = secrets.token_urlsafe(16)  # URL-safe

# ❌ WRONG - Predictable
import random
token = random.randbytes(16)  # DON'T USE
```

### 4. Set Security Headers
```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response
```

### 5. Use Threading Safely
```python
import threading

class SafeCounter:
    def __init__(self):
        self.value = 0
        self.lock = threading.RLock()  # Reentrant lock

    def increment(self):
        with self.lock:  # Always use context manager
            self.value += 1
            return self.value

    def get(self):
        with self.lock:
            return self.value  # Read under lock too!
```

---

## 🔒 Authentication & Authorization

### Check Token Properly
```python
def require_auth(required_scopes: Set[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(authorization: Optional[str] = Header(None), *args, **kwargs):
            # Validate header format
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing Authorization header")

            # Extract token
            token = authorization.split(" ", 1)[1]

            # Validate token
            token_info = token_manager.validate_token(token)

            # Check scopes
            if not required_scopes.issubset(token_info.scopes) and "admin" not in token_info.scopes:
                raise HTTPException(status_code=403, detail=f"Requires scopes: {required_scopes}")

            # Check rate limit
            rate_limiter.check_and_record(
                token_manager.get_token_fingerprint(token),
                token_info.rate_limits
            )

            # Pass token_info to handler
            return await func(token_info=token_info, *args, **kwargs)

        return wrapper
    return decorator

# Usage:
@app.get("/sensitive")
@require_auth({"admin"})
def sensitive_endpoint(token_info: TokenInfo):
    return {"data": "sensitive"}
```

---

## 🔐 Secrets Management

### Environment Variables
```bash
# .env (add to .gitignore!)
TRAPDOOR_TOKEN=90ac04027a0b4aba685dcae29eeed91a
TRAPDOOR_URL=https://your-instance.ngrok-free.dev

# Load in Python
from dotenv import load_dotenv
load_dotenv()

import os
TOKEN = os.getenv("TRAPDOOR_TOKEN")
```

### Keychain (macOS)
```bash
# Store in keychain
security add-generic-password -a "$USER" -s "trapdoor-token" -w "your-token-here"

# Read from keychain
security find-generic-password -a "$USER" -s "trapdoor-token" -w
```

### Never Commit These Files
```gitignore
# .gitignore
.env
.env.local
.env.production
config/tokens.json
**/secrets.json
**/*_credentials.json
**/auth_token.txt
```

---

## 🛡️ Rate Limiting

### Apply Rate Limits Everywhere
```python
# Per-token limits
rate_limits = {
    "requests_per_minute": 120,
    "requests_per_hour": 5000,
    "requests_per_day": 50000
}

# Per-operation limits
operation_limits = {
    "fs_write": {"requests_per_minute": 30},
    "fs_rm": {"requests_per_minute": 10},
    "exec": {"requests_per_minute": 20}
}

# Apply in endpoint
@app.post("/fs/write")
def write_file(token_info: TokenInfo, request: WriteRequest):
    # General rate limit
    rate_limiter.check_and_record(
        token_info.token_id,
        token_info.rate_limits
    )

    # Operation-specific limit
    if "fs_write" in token_info.operation_limits:
        rate_limiter.check_and_record(
            token_info.token_id,
            token_info.operation_limits["fs_write"],
            operation="fs_write"
        )

    # ... perform write
```

---

## 📝 Audit Logging

### Log Security Events
```python
import logging
import json
from datetime import datetime

audit_logger = logging.getLogger("trapdoor.audit")

def log_security_event(
    event_type: str,
    token_id: str,
    success: bool,
    details: dict
):
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "token_id": token_id,
        "success": success,
        "details": details
    }
    audit_logger.info(json.dumps(event))

# Usage:
log_security_event(
    "authentication",
    token_info.token_id,
    True,
    {"endpoint": "/fs/read", "path": "/etc/passwd", "result": "denied"}
)
```

### What to Log
✅ **Always log:**
- Authentication attempts (success and failure)
- Authorization failures
- Resource access (especially sensitive paths)
- Configuration changes
- Token operations (create, rotate, disable)
- Approval decisions

❌ **Never log:**
- Full authentication tokens
- Passwords
- API keys
- Personally identifiable information (PII)
- Credit card numbers
- SSH keys

---

## 🧪 Testing Security

### Unit Tests for Security
```python
import pytest

def test_path_traversal_blocked():
    token_info = create_test_token(scopes={"read"})

    # Try to escape allowed directory
    evil_path = Path("/allowed/dir/../../../etc/passwd")

    with pytest.raises(PermissionError):
        token_manager.check_permission(
            token_info,
            "fs_read",
            path=evil_path
        )

def test_command_injection_blocked():
    token_info = create_test_token(scopes={"exec"})

    # Try command injection
    evil_cmd = ["ls", "; rm -rf /"]

    with pytest.raises(PermissionError):
        token_manager.check_permission(
            token_info,
            "exec",
            command=evil_cmd
        )

def test_rate_limit_enforced():
    token_info = create_test_token()
    rate_limiter = RateLimiter()

    # Exhaust rate limit
    for i in range(120):
        rate_limiter.check_and_record(
            token_info.token_id,
            {"requests_per_minute": 120}
        )

    # Next request should fail
    with pytest.raises(RateLimitExceeded):
        rate_limiter.check_and_record(
            token_info.token_id,
            {"requests_per_minute": 120}
        )
```

---

## 🚨 Incident Response

### If Token is Compromised
```bash
# 1. Disable immediately
python3 -c "
from security import TokenManager
tm = TokenManager()
tm.disable_token('COMPROMISED_TOKEN_ID')
tm.save_tokens()
"

# 2. Check audit logs
grep "COMPROMISED_TOKEN_ID" logs/audit.log

# 3. Rotate all tokens (assume full compromise)
./control_panel.py  # Select "Rotate token"

# 4. Review access logs for suspicious activity
./scripts/audit_review.sh COMPROMISED_TOKEN_ID
```

### If Path Traversal is Exploited
```bash
# 1. Check what was accessed
grep "path_traversal\|permission_denied" logs/audit.log

# 2. Review file access logs
find /sensitive/dir -type f -mtime -1 -ls

# 3. Add affected paths to denylist
# Edit config/tokens.json:
"global_denylist": [
  "/etc/shadow",
  "/etc/passwd",
  "~/.ssh"
]

# 4. Restart services
./control_panel.py  # Stop and start
```

---

## 📚 Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

## ✅ Pre-Commit Checklist

Before committing code, verify:

- [ ] No hardcoded secrets or tokens
- [ ] All user input is validated
- [ ] Paths are normalized and checked
- [ ] Commands use array form, not shell strings
- [ ] Rate limiting applied to new endpoints
- [ ] Authentication required on sensitive endpoints
- [ ] Sensitive data not logged
- [ ] Security headers set on responses
- [ ] Thread-safe if using locks
- [ ] Tests include security cases
- [ ] Audit logging for security events

---

**Remember:** Security bugs are 10x harder to fix after deployment. Get it right the first time.
