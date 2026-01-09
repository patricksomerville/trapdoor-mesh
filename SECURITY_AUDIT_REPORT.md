# Trapdoor Security Audit Report
**Date:** 2025-10-28
**Auditor:** Claude Code Security Specialist
**Scope:** Comprehensive security analysis of Trapdoor AI agent control plane

---

## Executive Summary

**Overall Risk Level: HIGH**

Trapdoor is a security control plane for AI agents with filesystem and process access. While the security architecture shows good design principles with multi-token authentication, scoped permissions, and approval workflows, **several critical vulnerabilities have been identified** that require immediate remediation.

### Critical Findings
- **1 CRITICAL** - Hardcoded production credentials in source control
- **3 HIGH** - CORS misconfiguration, path traversal risks, approval queue race conditions
- **5 MEDIUM** - Input validation gaps, token exposure risks, missing security headers
- **4 LOW** - Logging improvements, rate limit enhancements

**Recommendation:** DO NOT deploy to production until Critical and High severity issues are resolved.

---

## OWASP Top 10 Compliance Matrix

| OWASP Category | Status | Findings |
|----------------|--------|----------|
| A01: Broken Access Control | ⚠️ PARTIAL | Path traversal risks, missing authorization checks |
| A02: Cryptographic Failures | ⚠️ PARTIAL | Hardcoded secrets, token exposure in connector |
| A03: Injection | ⚠️ PARTIAL | Command injection risks, missing input validation |
| A04: Insecure Design | ✅ GOOD | Strong security architecture with approval workflows |
| A05: Security Misconfiguration | ❌ FAIL | Overly permissive CORS, missing security headers |
| A06: Vulnerable Components | ℹ️ UNKNOWN | Dependencies not audited |
| A07: Auth/AuthN Failures | ⚠️ PARTIAL | Good token system, but session management gaps |
| A08: Software/Data Integrity | ✅ GOOD | No code execution from untrusted sources |
| A09: Logging/Monitoring | ⚠️ PARTIAL | Adequate logging but token exposure risks |
| A10: SSRF | ℹ️ N/A | No external request handling in core system |

---

## Detailed Findings

### CRITICAL SEVERITY

#### C-001: Hardcoded Production Credentials in Source Control
**File:** `/Users/patricksomerville/Desktop/Trapdoor/trapdoor_connector.py`
**Lines:** 29-31

**Vulnerability:**
```python
BASE_URL = "https://celsa-nonsimulative-wyatt.ngrok-free.dev"
TOKEN = "90ac04027a0b4aba685dcae29eeed91a"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
```

**Impact:**
- Production authentication token is hardcoded and committed to Git
- Token grants full admin access (verified in `config/tokens.json`)
- Anyone with repository access has complete control over the system
- ngrok URL exposes internal system to public internet with permanent credentials

**Exploitability:** TRIVIAL - Token is in plaintext in public code

**Proof of Concept:**
```bash
# Any attacker with repo access can execute:
curl -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a" \
  "https://celsa-nonsimulative-wyatt.ngrok-free.dev/fs/read?path=/etc/passwd"
```

**Remediation:**
1. **IMMEDIATE:** Revoke token `90ac04027a0b4aba685dcae29eeed91a` via control panel
2. Rotate all production tokens immediately
3. Remove hardcoded credentials from all files
4. Add `.env` file with credentials to `.gitignore`
5. Update connector to load from environment variables:
```python
import os
BASE_URL = os.getenv("TRAPDOOR_URL", "http://localhost:8080")
TOKEN = os.getenv("TRAPDOOR_TOKEN")
if not TOKEN:
    raise ValueError("TRAPDOOR_TOKEN environment variable required")
```
6. Audit Git history and consider it compromised - all historical tokens must be rotated

**Status:** UNRESOLVED - URGENT ACTION REQUIRED

---

### HIGH SEVERITY

#### H-001: Overly Permissive CORS Configuration
**File:** `/Users/patricksomerville/Desktop/Trapdoor/chatgpt_proxy.py`
**Line:** 31

**Vulnerability:**
```python
CORS(app)  # Allow requests from any origin
```

**Impact:**
- Any website can make authenticated requests to the proxy
- Enables Cross-Site Request Forgery (CSRF) attacks
- Malicious JavaScript from any domain can access the API
- Token theft via XSS on unrelated domains

**Attack Scenario:**
1. User visits malicious website `evil.com`
2. JavaScript reads token from localStorage or makes authenticated requests
3. Attacker gains full filesystem/command execution access

**Remediation:**
```python
# Restrict to specific origins
CORS(app, origins=[
    "http://localhost:3000",  # Local development
    "https://chat.openai.com",  # If needed
])

# Or disable completely if not needed:
# CORS(app, origins=[])
```

**Additional Security Headers Required:**
```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

**Status:** UNRESOLVED

---

#### H-002: Path Traversal Vulnerability Risk
**File:** `/Users/patricksomerville/Desktop/Trapdoor/security.py`
**Lines:** 273-298

**Vulnerability:**
Path validation uses `startswith()` after resolution, but doesn't validate path components before resolution. This can be exploited with symlinks and race conditions.

**Current Implementation:**
```python
def _check_path_allowed(self, token_info: TokenInfo, path: Path) -> bool:
    path_str = str(path.resolve())  # Resolves AFTER receiving user input

    # Check denylists
    for denied in self.global_denylist:
        denied_path = str(Path(denied).expanduser().resolve())
        if path_str.startswith(denied_path):  # Only checks prefix
            return False
```

**Issues:**
1. **Symlink exploitation:** If user creates symlink from allowed dir to denied dir, resolution happens after validation decision point
2. **TOCTOU race condition:** Path can be changed between validation and use
3. **Bypass via traversal:** Patterns like `/allowed/../../../etc/passwd` may resolve after validation
4. **Case sensitivity:** No normalization for case-insensitive filesystems (macOS default)

**Attack Scenario:**
```bash
# Assume /tmp is allowed but ~/.ssh is denied
ln -s ~/.ssh /tmp/ssh_link
# Request /tmp/ssh_link/id_rsa - may bypass denylist
```

**Remediation:**
```python
def _check_path_allowed(self, token_info: TokenInfo, path: Path) -> bool:
    # Validate and normalize FIRST
    try:
        # Resolve and validate in one step
        path_resolved = path.expanduser().resolve(strict=True)  # strict=True ensures exists
        path_str = str(path_resolved)

        # Prevent traversal attempts
        if ".." in path.parts:
            return False

        # Check if real path (no symlinks) is allowed
        path_real = str(path_resolved.resolve())

    except (OSError, RuntimeError):
        return False  # Invalid path

    # Check global denylist with real paths
    for denied in self.global_denylist:
        denied_real = str(Path(denied).expanduser().resolve())
        # Check both resolved and real paths
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

**Additional Recommendations:**
- Implement file operation sandboxing with chroot/containers
- Add filesystem capability restrictions (read-only mode, no symlink creation)
- Log all path access attempts for anomaly detection

**Status:** UNRESOLVED

---

#### H-003: Approval Queue Race Condition
**File:** `/Users/patricksomerville/Desktop/Trapdoor/security.py`
**Lines:** 519-543

**Vulnerability:**
The approval checking mechanism has a race condition that could allow unapproved operations to execute.

**Problematic Code:**
```python
def check_approval(self, request_id: str, timeout: int = 30) -> bool:
    start = time.time()

    while time.time() - start < timeout:
        with self.lock:
            if request_id not in self.pending:
                return False

            op = self.pending[request_id]
            if op.status == "approved":
                del self.pending[request_id]  # Delete INSIDE lock
                return True
            elif op.status == "denied":
                del self.pending[request_id]
                return False

        time.sleep(0.5)  # Sleep OUTSIDE lock - race window!
```

**Race Condition:**
1. Thread A checks status, finds "pending"
2. Lock is released, Thread A sleeps
3. Admin thread approves the request
4. Thread B (different operation) starts checking
5. Thread A wakes up, re-acquires lock
6. **Race:** Both threads could read "approved" if timing aligns

**Additional Issue - Polling Anti-Pattern:**
- Busy-wait with 500ms sleep wastes CPU
- Timeout of 30s means operations can hang for extended periods
- No notification mechanism for approval state changes

**Remediation:**
```python
from threading import Event, RLock

class ApprovalQueue:
    def __init__(self):
        self.pending: Dict[str, PendingOperation] = {}
        self.lock = RLock()
        self.events: Dict[str, Event] = {}  # Add event notifications

    def request_approval(self, operation: str, details: Dict[str, Any]) -> str:
        request_id = secrets.token_hex(8)

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
        # Get event before checking status
        with self.lock:
            if request_id not in self.events:
                return False
            event = self.events[request_id]

        # Wait for event notification (no polling!)
        if not event.wait(timeout=timeout):
            # Timeout
            with self.lock:
                self.pending.pop(request_id, None)
                self.events.pop(request_id, None)
            return False

        # Check final status
        with self.lock:
            op = self.pending.get(request_id)
            if op and op.status == "approved":
                self.pending.pop(request_id, None)
                self.events.pop(request_id, None)
                return True
            else:
                self.pending.pop(request_id, None)
                self.events.pop(request_id, None)
                return False

    def approve(self, request_id: str) -> bool:
        with self.lock:
            if request_id in self.pending:
                self.pending[request_id].status = "approved"
                if request_id in self.events:
                    self.events[request_id].set()  # Notify waiters
                return True
        return False

    def deny(self, request_id: str) -> bool:
        with self.lock:
            if request_id in self.pending:
                self.pending[request_id].status = "denied"
                if request_id in self.events:
                    self.events[request_id].set()  # Notify waiters
                return True
        return False
```

**Status:** UNRESOLVED

---

### MEDIUM SEVERITY

#### M-001: Missing Input Validation on Critical Endpoints
**Files:** `approval_endpoints.py`, `chatgpt_proxy.py`

**Vulnerability:**
Request bodies are not validated for type, size, or format before processing.

**Examples:**

**approval_endpoints.py - Lines 24-41:**
```python
def list_pending_approvals(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")

    token = authorization.split(" ", 1)[1]  # No validation of token format
    # What if authorization = "Bearer "? IndexError
```

**chatgpt_proxy.py - Lines 50-69:**
```python
def chat():
    data = request.get_json()  # No size limit!
    prompt = data.get('prompt', '')  # No type validation
    # What if prompt is 10GB of data? DoS
    # What if prompt is not a string? TypeError
```

**Impact:**
- Denial of Service via oversized requests
- Type confusion errors causing crashes
- Injection attacks via malformed data
- Resource exhaustion

**Remediation:**

**For FastAPI endpoints:**
```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = Field(default="qwen2.5-coder:32b", max_length=100)

    @validator('prompt')
    def validate_prompt(cls, v):
        if not isinstance(v, str):
            raise ValueError('prompt must be a string')
        # Additional validation
        return v

@app.post('/chat')
def chat(request: ChatRequest):  # Automatic validation
    response = td.chat(request.prompt, request.model)
    return {"response": response}
```

**For Flask endpoints:**
```python
from flask import request, jsonify
import json

MAX_REQUEST_SIZE = 1024 * 1024  # 1MB

@app.before_request
def check_request_size():
    if request.content_length and request.content_length > MAX_REQUEST_SIZE:
        return jsonify({"error": "Request too large"}), 413

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(force=True, silent=False)
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON object"}), 400

        prompt = data.get('prompt')
        if not isinstance(prompt, str):
            return jsonify({"error": "prompt must be a string"}), 400
        if len(prompt) < 1 or len(prompt) > 10000:
            return jsonify({"error": "prompt length must be 1-10000 chars"}), 400

        response = td.chat(prompt)
        return jsonify({"response": response})

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

**Status:** UNRESOLVED

---

#### M-002: Token Exposure in Debug Output
**File:** `/Users/patricksomerville/Desktop/Trapdoor/approval_endpoints.py`
**Lines:** 92-120

**Vulnerability:**
Debug print statements log sensitive operations without redacting tokens.

```python
@app.get("/tokens/list")
def list_tokens(authorization: Optional[str] = Header(None)):
    print("[DEBUG] /tokens/list called")
    # ... token validation ...
    print(f"[DEBUG] Serializing {len(token_manager.tokens)} tokens")
```

**Issues:**
1. Debug output may log authorization headers in other parts of code
2. Token values are serialized to JSON (line 119) - risk if logs are captured
3. No log level controls - always prints

**Impact:**
- Token leakage in log files
- Unauthorized access if logs are compromised
- Compliance violations (PCI, HIPAA, etc.)

**Remediation:**
```python
import logging

# Configure proper logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create filter to redact tokens
class TokenRedactingFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'msg'):
            # Redact Bearer tokens
            record.msg = re.sub(
                r'Bearer [a-f0-9]{32}',
                'Bearer [REDACTED]',
                str(record.msg)
            )
        return True

logger.addFilter(TokenRedactingFilter())

@app.get("/tokens/list")
def list_tokens(authorization: Optional[str] = Header(None)):
    logger.info("Token list requested")  # No token value
    # ...
    logger.debug(f"Serializing {len(token_manager.tokens)} tokens")  # Only in debug mode
```

**Never Log:**
- Full authentication tokens
- Passwords or credentials
- API keys
- Session IDs
- Personal data

**Status:** UNRESOLVED

---

#### M-003: Rate Limit Bypass via Token Fingerprinting
**File:** `/Users/patricksomerville/Desktop/Trapdoor/security.py`
**Line:** 486-488

**Vulnerability:**
```python
def get_token_fingerprint(self, token: str) -> str:
    """Generate token fingerprint for rate limiting"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
```

**Issues:**
1. Only 12 characters of SHA256 = 48 bits of entropy
2. Birthday paradox: ~50% collision probability after 2^24 ≈ 16M tokens
3. Attacker can generate tokens until collision found, bypassing rate limits
4. Truncation weakens cryptographic hash properties

**Impact:**
- Rate limit bypass with enough token attempts
- Multiple tokens can share same rate limit bucket
- Distributed attacks can pool rate limits

**Remediation:**
```python
def get_token_fingerprint(self, token: str) -> str:
    """Generate token fingerprint for rate limiting"""
    # Use full hash for rate limiting - storage is cheap
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# Or use token_id directly (more explicit):
def get_rate_limit_key(self, token_info: TokenInfo) -> str:
    """Get rate limit key for token"""
    return f"token:{token_info.token_id}"
```

**Additional Recommendation:**
Implement per-IP rate limiting in addition to per-token:
```python
def check_and_record(
    self,
    token_fp: str,
    client_ip: str,  # Add IP parameter
    limits: Dict[str, int],
    operation: Optional[str] = None
) -> None:
    # Rate limit by token
    self._check_window(...)

    # Also rate limit by IP (prevents token generation attacks)
    ip_limits = {"requests_per_minute": 300}
    self._check_window(..., key=f"ip:{client_ip}", ...)
```

**Status:** UNRESOLVED

---

#### M-004: Insufficient Token Expiration Handling
**File:** `/Users/patricksomerville/Desktop/Trapdoor/security.py`
**Lines:** 215-217

**Vulnerability:**
```python
if token_info.expires and datetime.now() > token_info.expires:
    raise TokenExpiredError(f"Token expired on {token_info.expires.isoformat()}")
```

**Issues:**
1. Expired tokens remain in storage indefinitely
2. No cleanup mechanism for old tokens
3. No grace period for clock skew
4. Token lookup table never cleared of expired entries

**Impact:**
- Storage bloat over time
- Expired tokens can be analyzed for patterns
- Memory exhaustion with enough expired tokens
- Confusion about which tokens are active

**Remediation:**
```python
# Add cleanup method
def cleanup_expired_tokens(self) -> int:
    """Remove expired tokens from storage. Returns count removed."""
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

# Run cleanup periodically
import threading

def _start_cleanup_thread(self):
    def cleanup_worker():
        while True:
            time.sleep(3600)  # Every hour
            count = self.cleanup_expired_tokens()
            if count > 0:
                logger.info(f"Cleaned up {count} expired tokens")

    thread = threading.Thread(target=cleanup_worker, daemon=True)
    thread.start()

# Add grace period for clock skew
CLOCK_SKEW_SECONDS = 300  # 5 minutes

if token_info.expires and datetime.now() > (token_info.expires + timedelta(seconds=CLOCK_SKEW_SECONDS)):
    raise TokenExpiredError(f"Token expired on {token_info.expires.isoformat()}")
```

**Status:** UNRESOLVED

---

#### M-005: Command Injection Risk in Subprocess Execution
**File:** `/Users/patricksomerville/Desktop/Trapdoor/control_panel.py`
**Lines:** 128-142

**Vulnerability:**
```python
def run_script(script_name: str, args: list[str] | None = None, env: Optional[Dict[str, str]] = None) -> int:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"⚠️  Script missing: {script_path}")
        return 1
    cmd = ["bash", str(script_path)]
    if args:
        cmd.extend(args)  # No validation of args!
```

**Issues:**
1. `args` parameter not validated before passing to subprocess
2. Shell metacharacters in args can escape to bash
3. Script names not validated - could include path traversal
4. No input sanitization

**Attack Scenario:**
```python
# If attacker controls args:
run_script("legitimate.sh", ["normal_arg", "; rm -rf /"])
# Executes: bash legitimate.sh normal_arg ; rm -rf /
```

**Remediation:**
```python
import shlex

def run_script(script_name: str, args: list[str] | None = None, env: Optional[Dict[str, str]] = None) -> int:
    # Validate script name (no path traversal)
    if ".." in script_name or "/" in script_name:
        print("⚠️  Invalid script name")
        return 1

    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"⚠️  Script missing: {script_path}")
        return 1

    # Validate script path is within SCRIPTS_DIR
    try:
        script_path = script_path.resolve(strict=True)
        if not str(script_path).startswith(str(SCRIPTS_DIR.resolve())):
            print("⚠️  Script path outside allowed directory")
            return 1
    except (OSError, RuntimeError):
        print("⚠️  Invalid script path")
        return 1

    # Build command with validated args
    cmd = ["bash", str(script_path)]
    if args:
        # Validate each argument
        for arg in args:
            if not isinstance(arg, str):
                print("⚠️  Invalid argument type")
                return 1
            # Check for shell metacharacters
            if any(c in arg for c in [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n']):
                print(f"⚠️  Invalid characters in argument: {arg}")
                return 1
            cmd.append(arg)

    try:
        # shell=False is correct (not using shell=True)
        completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env)
        return completed.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Cancelled.")
        return 130
```

**Status:** UNRESOLVED

---

### LOW SEVERITY

#### L-001: Weak Token Generation for Request IDs
**File:** `/Users/patricksomerville/Desktop/Trapdoor/security.py`
**Line:** 506

**Vulnerability:**
```python
request_id = secrets.token_hex(8)  # Only 8 bytes = 64 bits
```

**Issue:**
- 64-bit IDs can collide after ~4 billion requests (birthday paradox)
- Predictable sequence if attacker can observe multiple IDs
- Not sufficient for long-running systems

**Remediation:**
```python
# Use 16 bytes for 128-bit security
request_id = secrets.token_hex(16)

# Or use UUID4
import uuid
request_id = str(uuid.uuid4())
```

**Status:** UNRESOLVED

---

#### L-002: Missing Security Headers on HTTP Responses
**File:** `chatgpt_proxy.py`

**Issue:**
No security headers set on HTTP responses:
- No `X-Content-Type-Options: nosniff`
- No `X-Frame-Options: DENY`
- No `Content-Security-Policy`
- No `X-XSS-Protection`

**Remediation:**
See H-001 remediation for full security headers implementation.

**Status:** UNRESOLVED

---

#### L-003: No Rate Limit for Approval Operations
**File:** `approval_endpoints.py`

**Issue:**
Approval endpoints (`/approval/pending`, `/approval/{id}/approve`, `/approval/{id}/deny`) have no rate limiting. Admin token could be brute-forced or approval queue could be flooded.

**Remediation:**
Add rate limiting to approval endpoints:
```python
@app.post("/approval/{request_id}/approve")
def approve_operation(request_id: str, authorization: Optional[str] = Header(None)):
    # Validate token
    token = authorization.split(" ", 1)[1]
    token_info = token_manager.validate_token(token)

    # Rate limit approval operations
    rate_limiter.check_and_record(
        rate_limiter.get_token_fingerprint(token_info.token),
        {"requests_per_minute": 10},  # Stricter limit for sensitive ops
        operation="approval"
    )

    # ... rest of function
```

**Status:** UNRESOLVED

---

#### L-004: JSON File Handling Race Condition
**File:** `/Users/patricksomerville/Desktop/Trapdoor/security.py`
**Lines:** 184-198

**Issue:**
Token storage uses simple JSON file I/O without atomic writes:
```python
def save_tokens(self) -> None:
    with self.lock:
        # ... prepare config dict ...
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
```

**Problems:**
1. File corruption if process crashes during write
2. Race condition if multiple processes access same file
3. No backup of previous state
4. No file locking across processes

**Remediation:**
```python
import tempfile
import shutil

def save_tokens(self) -> None:
    with self.lock:
        config = {
            "tokens": [t.to_dict() for t in self.tokens.values()],
            "global_rules": {
                "global_denylist": self.global_denylist,
                "require_approval_operations": list(self.require_approval_operations)
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        fd, temp_path = tempfile.mkstemp(
            dir=self.config_path.parent,
            prefix=".tokens.",
            suffix=".tmp"
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            # Atomic rename
            shutil.move(temp_path, self.config_path)

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
```

**Status:** UNRESOLVED

---

## Additional Security Recommendations

### 1. Implement Comprehensive Audit Logging
Currently missing:
- Who accessed what resources
- Failed authentication attempts
- Permission denied events
- Approval decisions with approver identity

**Recommendation:**
```python
import logging
import json
from datetime import datetime

audit_logger = logging.getLogger("trapdoor.audit")
audit_logger.setLevel(logging.INFO)
handler = logging.FileHandler("logs/audit.log")
handler.setFormatter(logging.Formatter('%(message)s'))
audit_logger.addHandler(handler)

def log_audit_event(event_type: str, token_id: str, details: dict):
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "token_id": token_id,
        "details": details
    }
    audit_logger.info(json.dumps(event))

# Usage:
log_audit_event("fs_access", token_info.token_id, {
    "operation": "read",
    "path": "/etc/passwd",
    "result": "denied",
    "reason": "path_in_denylist"
})
```

### 2. Add Security Testing
Missing test coverage for:
- Path traversal attempts
- Token expiration edge cases
- Rate limit bypass attempts
- Approval workflow race conditions

**Recommendation:**
Create `tests/security/` directory with:
- `test_path_traversal.py`
- `test_authentication.py`
- `test_rate_limiting.py`
- `test_approval_queue.py`

### 3. Dependency Security Audit
Audit all dependencies for known vulnerabilities:
```bash
pip install safety
safety check --json

# For JavaScript dependencies (if any)
npm audit
```

### 4. Implement Token Rotation Policy
- Enforce automatic rotation every 90 days
- Send notifications before expiration
- Implement grace period for rotation

### 5. Add Intrusion Detection
Monitor for:
- Unusual access patterns
- High rate of denied requests
- Access to sensitive paths
- Token reuse across different IPs
- Approval queue manipulation attempts

---

## Risk Prioritization

### Immediate Action Required (0-7 days)
1. **C-001:** Rotate all compromised tokens, remove from code
2. **H-001:** Fix CORS configuration
3. **H-002:** Implement proper path validation
4. **H-003:** Fix approval queue race condition

### Short Term (1-4 weeks)
5. **M-001:** Add input validation to all endpoints
6. **M-002:** Implement secure logging
7. **M-003:** Fix rate limit fingerprinting
8. **M-004:** Add token expiration cleanup
9. **M-005:** Validate subprocess arguments

### Medium Term (1-3 months)
10. Implement comprehensive audit logging
11. Add security test suite
12. Perform dependency security audit
13. Add intrusion detection
14. Implement token rotation policy

---

## Testing Recommendations

### Security Test Plan

**Phase 1: Immediate Verification**
```bash
# Test C-001: Verify token rotation
curl -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a" \
  http://localhost:8080/health
# Should return 401 after rotation

# Test H-001: CORS
curl -H "Origin: https://evil.com" \
  -H "Authorization: Bearer NEW_TOKEN" \
  http://localhost:5001/health
# Should be blocked

# Test H-002: Path traversal
curl -H "Authorization: Bearer NEW_TOKEN" \
  "http://localhost:8080/fs/read?path=/tmp/../../../etc/passwd"
# Should return 403
```

**Phase 2: Fuzzing**
```python
# Install fuzzer
pip install hypothesis

# Fuzz path validation
@given(st.text())
def test_path_validation_fuzz(path):
    try:
        result = token_manager._check_path_allowed(token_info, Path(path))
        # Should never crash, always return bool
        assert isinstance(result, bool)
    except (OSError, ValueError):
        pass  # Expected for invalid paths
```

**Phase 3: Penetration Testing**
- Hire external security firm
- Perform black-box testing
- Test approval workflow timing attacks
- Attempt privilege escalation

---

## Compliance Considerations

### GDPR
- Audit logging must include data access records
- Token expiration must be enforced
- User data deletion must cascade to tokens

### SOC 2
- All access must be logged
- Approval workflows must be auditable
- Token rotation must be enforced

### PCI DSS
- No payment data should be accessible via Trapdoor
- If payment systems are accessed, additional controls required

---

## Conclusion

Trapdoor has a **solid security architecture** with good design principles including:
- ✅ Multi-token authentication system
- ✅ Scoped permissions (read/write/exec/admin)
- ✅ Approval workflows for destructive operations
- ✅ Rate limiting framework
- ✅ Path and command allowlists/denylists

However, **critical implementation vulnerabilities** prevent production deployment:
- ❌ Hardcoded production credentials
- ❌ Overly permissive CORS
- ❌ Path traversal risks
- ❌ Approval queue race conditions
- ❌ Missing input validation

**Recommendation:** Address all Critical and High severity findings before production use. System shows promise but requires security hardening.

---

## Files Audited
- `/Users/patricksomerville/Desktop/Trapdoor/security.py` (726 lines)
- `/Users/patricksomerville/Desktop/Trapdoor/approval_endpoints.py` (173 lines)
- `/Users/patricksomerville/Desktop/Trapdoor/control_panel.py` (442 lines)
- `/Users/patricksomerville/Desktop/Trapdoor/chatgpt_proxy.py` (231 lines)
- `/Users/patricksomerville/Desktop/Trapdoor/trapdoor_connector.py` (277 lines)
- `/Users/patricksomerville/Desktop/Trapdoor/config/tokens.json` (33 lines)

**Total Lines of Code Reviewed:** ~1,882

---

**Report Generated:** 2025-10-28
**Classification:** CONFIDENTIAL
**Next Review:** After remediation of Critical/High findings
