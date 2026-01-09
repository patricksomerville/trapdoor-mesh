---
status: pending
priority: p2
issue_id: "003"
tags: [security, web, flask, cors, code-review]
dependencies: []
---

# Fix CORS Misconfiguration in ChatGPT Proxy

## Problem Statement

The Flask proxy (`chatgpt_proxy.py`) uses `CORS(app)` with no restrictions, allowing **any origin** to make requests. This enables Cross-Site Request Forgery (CSRF) attacks and unauthorized access from malicious websites.

## Findings

- **Discovered during:** Security audit by security-sentinel agent
- **Location:** `chatgpt_proxy.py:31`
- **Current config:** `CORS(app)` - allows all origins
- **Impact:** CSRF vulnerability, cross-site abuse

**Current Implementation:**
```python
app = Flask(__name__)
CORS(app)  # ❌ Allows ANY origin
```

## Impact Assessment

**Severity:** 🟠 HIGH

**Security Risks:**
- Malicious websites can make requests to Flask proxy
- CSRF attacks possible (e.g., file writes, command execution)
- No protection against cross-site abuse
- Potential data exfiltration via JavaScript

**Attack Scenario:**
1. User visits malicious website while Flask proxy is running
2. Malicious JavaScript makes requests to `http://localhost:5001`
3. Proxy accepts request (CORS allows it)
4. Attacker executes commands, reads files, etc.

## Proposed Solutions

### Option 1: Localhost Only (Recommended)
```python
from flask_cors import CORS

CORS(app, origins=[
    "http://localhost:*",
    "http://127.0.0.1:*"
])
```

- **Pros**: Simple, secure for local-only usage
- **Cons**: Won't work from LAN devices
- **Effort**: Small (5 minutes)
- **Risk**: Low

### Option 2: Environment Variable Configuration
```python
import os
from flask_cors import CORS

ALLOWED_ORIGINS = os.environ.get(
    "TRAPDOOR_CORS_ORIGINS",
    "http://localhost:5001,http://127.0.0.1:5001"
).split(",")

CORS(app, origins=ALLOWED_ORIGINS)
```

- **Pros**: Flexible, can allow specific origins when needed
- **Cons**: Must configure env var
- **Effort**: Small (15 minutes)
- **Risk**: Low

### Option 3: Disable CORS (Most Secure)
```python
# Remove CORS entirely
# app = Flask(__name__)
# CORS(app)  # ← Delete this line
```

- **Pros**: Maximum security
- **Cons**: May break some client scenarios
- **Effort**: Trivial (1 minute)
- **Risk**: Low

## Recommended Action

**Implement Option 2** (environment variable configuration with localhost default)

**Implementation:**
```python
import os
from flask_cors import CORS

# Default to localhost only
ALLOWED_ORIGINS = os.environ.get(
    "TRAPDOOR_PROXY_CORS_ORIGINS",
    "http://localhost:*,http://127.0.0.1:*"
).split(",")

CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)
```

**Update Documentation:**
Add to `CHATGPT_PROXY_GUIDE.md`:
```markdown
## CORS Configuration

By default, the proxy only accepts requests from localhost. To allow other origins:

```bash
export TRAPDOOR_PROXY_CORS_ORIGINS="http://localhost:*,http://192.168.1.100:*"
python3 chatgpt_proxy.py
```
```

## Technical Details

- **Affected Files**:
  - `/Users/patricksomerville/Desktop/Trapdoor/chatgpt_proxy.py` (line 31)
  - `/Users/patricksomerville/Desktop/Trapdoor/CHATGPT_PROXY_GUIDE.md` (documentation)

- **Related Components**:
  - Flask proxy server
  - ChatGPT integration
  - Trapdoor connector client

- **Database Changes**: No

## Acceptance Criteria

- [ ] CORS restricted to localhost by default
- [ ] Environment variable override available
- [ ] Documentation updated
- [ ] Test: External origin rejected
- [ ] Test: Localhost origin accepted
- [ ] Code review completed

## Work Log

### 2025-10-28 - Code Review Discovery
**By:** security-sentinel agent
**Actions:**
- Identified unrestricted CORS configuration
- Analyzed CSRF attack vectors
- Proposed secure configuration

## Notes

**Priority:** P2 (High) - Security issue but requires local proxy running + malicious website visit.

**Created:** 2025-10-28
