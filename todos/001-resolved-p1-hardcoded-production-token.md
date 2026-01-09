---
status: resolved
priority: p1
issue_id: "001"
tags: [security, credentials, code-review]
dependencies: []
resolved_date: 2025-10-28
---

# Remove Hardcoded Production Token from Source

## Problem Statement

The production admin token `90ac04027a0b4aba685dcae29eeed91a` is hardcoded in `trapdoor_connector.py` and has been committed to Git. This presents an **immediate security risk** as anyone with access to the repository has full admin privileges to Trapdoor.

## Findings

- **Discovered during:** Comprehensive security audit by security-sentinel agent
- **Location:** `trapdoor_connector.py:38-39`
- **Token value:** `90ac04027a0b4aba685dcae29eeed91a` (admin scope)
- **Exposure:** Committed in initial Git commit on 2025-10-28
- **Scope:** Full admin access (read, write, exec, destructive operations)

**Code snippet:**
```python
BASE_URL = "https://celsa-nonsimulative-wyatt.ngrok-free.dev"
TOKEN = "90ac04027a0b4aba685dcae29eeed91a"  # ❌ ADMIN TOKEN IN SOURCE
```

## Impact Assessment

**Severity:** 🔴 CRITICAL

**Security Risks:**
- Anyone with Git repository access has full admin control over Trapdoor
- Token is in Git history permanently (even if removed from current files)
- If repository is ever made public, entire system is compromised
- Violates fundamental security practice: never commit credentials

**Attack Scenarios:**
1. Unauthorized access to filesystem via Trapdoor API
2. Execution of arbitrary commands with admin privileges
3. Token theft from Git history
4. Lateral movement if repo is cloned to other machines

## Proposed Solutions

### Option 1: Environment Variable (Recommended for Uploads)
```python
import os

TOKEN = os.environ.get("TRAPDOOR_TOKEN")
if not TOKEN:
    raise ValueError(
        "TRAPDOOR_TOKEN environment variable required.\n"
        "Set with: export TRAPDOOR_TOKEN=your-token-here"
    )
```

- **Pros**:
  - Standard practice for credentials
  - Works in uploaded environments (ChatGPT Code Interpreter)
  - No files to manage
  - Easy to rotate
- **Cons**:
  - Must set env var before running
  - Can be forgotten in new shells
- **Effort**: Small (5 minutes)
- **Risk**: Low

### Option 2: Config File (Recommended for Local Use)
```python
from pathlib import Path

def load_token() -> str:
    """Load token from config file"""
    token_file = Path.home() / ".trapdoor" / "token"
    if not token_file.exists():
        raise ValueError(
            f"Token file not found: {token_file}\n"
            f"Create with: echo 'YOUR_TOKEN' > {token_file}"
        )
    return token_file.read_text().strip()

TOKEN = load_token()
```

- **Pros**:
  - Persists across sessions
  - Standard Unix pattern (~/.config/app)
  - Single setup step
- **Cons**:
  - Doesn't work in sandboxed environments
  - File permissions must be managed
- **Effort**: Small (10 minutes)
- **Risk**: Low

### Option 3: Hybrid Approach (Best of Both)
```python
import os
from pathlib import Path

def get_token() -> str:
    """Get token from env var or config file"""
    # Try environment variable first
    token = os.environ.get("TRAPDOOR_TOKEN")
    if token:
        return token

    # Fall back to config file
    token_file = Path.home() / ".trapdoor" / "token"
    if token_file.exists():
        return token_file.read_text().strip()

    raise ValueError(
        "No token found. Either:\n"
        "  1. Set TRAPDOOR_TOKEN environment variable, or\n"
        f"  2. Create {token_file} with your token"
    )

TOKEN = get_token()
```

- **Pros**:
  - Works in any environment
  - Flexible deployment
  - Clear error messages
- **Cons**:
  - Slightly more complex
- **Effort**: Small (15 minutes)
- **Risk**: Low

## Recommended Action

**Immediate (Today):**
1. **Disable compromised token** in `config/tokens.json`:
   ```bash
   # Edit tokens.json, set enabled: false for token_id "migrated_1"
   ```

2. **Generate new admin token**:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(16))"
   # Save output as new admin token
   ```

3. **Update `config/tokens.json`** with new token

4. **Implement Option 3** (hybrid approach) in `trapdoor_connector.py`

5. **Test with new token**:
   ```python
   import trapdoor_connector as td
   print(td.health())  # Should work with new token
   ```

6. **Update documentation** (`README.md`, `CLIENT_EXAMPLES.md`) with token setup instructions

7. **Add to `.gitignore`** (if not already):
   ```
   .trapdoor/token
   .env
   auth_token.txt
   ```

**This Week:**
- Consider using Git filter to remove token from history (advanced, optional)
- Update all client integrations with new token

## Technical Details

- **Affected Files**:
  - `/Users/patricksomerville/Desktop/Trapdoor/trapdoor_connector.py` (lines 38-39)
  - `/Users/patricksomerville/Desktop/Trapdoor/config/tokens.json` (token to disable)
  - Documentation files mentioning token setup

- **Related Components**:
  - Token authentication system
  - Client connector module
  - All services using trapdoor_connector.py

- **Database Changes**: No

- **Git History Impact**: Token is in commit `b19c936` (initial commit)

## Resources

- **Security Audit Report**: `SECURITY_AUDIT_REPORT.md`
- **Security Action Items**: `SECURITY_ACTION_ITEMS.md`
- **Original Token Config**: `config/tokens.json`
- **OWASP Guidelines**: [Credential Management](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Storage_Cheat_Sheet.html)

## Acceptance Criteria

- [ ] Hardcoded token removed from `trapdoor_connector.py`
- [ ] Token loading implemented (env var or config file)
- [ ] Old token disabled in `config/tokens.json`
- [ ] New admin token generated and configured
- [ ] Token setup documented in README
- [ ] `.gitignore` updated to exclude token files
- [ ] All tests pass with new token
- [ ] Client examples updated
- [ ] Code review completed

## Work Log

### 2025-10-28 - Code Review Discovery
**By:** Claude Code Review System (security-sentinel agent)
**Actions:**
- Discovered hardcoded token during comprehensive security audit
- Analyzed exposure in Git history
- Evaluated impact and attack scenarios
- Proposed remediation strategies

**Learnings:**
- Hardcoded credentials are a critical vulnerability even in personal projects
- Git history preserves secrets indefinitely
- Token rotation requires coordinated updates across all clients
- Environment variables are the standard solution for portable code

## Notes

**Philosophy Alignment:**
From CLAUDE.md: "Build for yourself. Ship to yourself first. Find pain, fix pain."

This is a **real security issue** discovered through real code review, not a hypothetical concern. Fixing it maintains the philosophy of "no demo modes" - if the token can be compromised, it WILL be compromised.

**Urgency:** This is production infrastructure with an exposed admin token. Fix today.

**Created:** 2025-10-28
**Source:** Comprehensive code review (`/compounding-engineering:review`)
