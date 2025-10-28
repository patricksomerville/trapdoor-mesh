

# Trapdoor Security Enhancement Integration Guide

**Date:** October 28, 2025  
**Status:** Ready for Integration  
**Backward Compatible:** ✅ Yes

---

## Quick Start

### 1. Generate Example Configuration

```bash
cd ~/Desktop/Trapdoor
python3 security.py generate
```

This creates `config/tokens.example.json` with sample configurations.

### 2. Migrate Existing Tokens (Optional)

If you have existing `AUTH_TOKEN` or `AUTH_TOKEN_FILE`:

```bash
python3 security.py migrate
```

This creates `config/tokens.json` with your existing tokens (granted `admin` scope).

### 3. Test the Security Module

```bash
python3 security.py
# Shows usage instructions

python3 -c "from security import TokenManager; tm = TokenManager(); print(f'Loaded {len(tm.tokens)} tokens')"
```

---

## Integration Steps

### Step 1: Update local_agent_server.py Imports

Add these imports at the top of `local_agent_server.py`:

```python
# Add after existing imports
from security_integration import (
    setup_security,
    require_auth_and_permission,
    get_approval_queue,
    get_token_manager
)
from approval_endpoints import register_approval_endpoints
```

### Step 2: Initialize Security System

Add this after the FastAPI app creation (after `app = FastAPI()`):

```python
# Initialize enhanced security system
try:
    token_manager, rate_limiter, approval_queue = setup_security(
        config_path=Path("config/tokens.json"),
        auto_migrate=True  # Automatically migrate from AUTH_TOKEN
    )
    
    # Register approval management endpoints
    register_approval_endpoints(app, token_manager, approval_queue)
    
    print("✅ Enhanced security system enabled")
    SECURITY_ENHANCED = True
except Exception as e:
    print(f"⚠️  Security enhancement disabled: {e}")
    print("⚠️  Falling back to legacy AUTH_TOKEN system")
    SECURITY_ENHANCED = False
```

### Step 3: Update Endpoint Authentication

Replace `_require_auth()` calls with `require_auth_and_permission()`:

#### Before (fs_ls endpoint):
```python
@app.get("/fs/ls")
def fs_ls(path: Optional[str] = None, authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    tgt = _resolve_path(path or str(BASE_DIR))
    # ...
```

#### After (fs_ls endpoint):
```python
@app.get("/fs/ls")
def fs_ls(path: Optional[str] = None, authorization: Optional[str] = Header(None)):
    if SECURITY_ENHANCED:
        token_info = require_auth_and_permission(
            authorization=authorization,
            operation="fs_ls",
            path=_resolve_path(path or str(BASE_DIR)) if path else None
        )
        token_fp = rate_limiter.get_token_fingerprint(token_info.token)
    else:
        token_fp = _require_auth(authorization)
    
    tgt = _resolve_path(path or str(BASE_DIR))
    # ... rest of function
```

### Step 4: Update All Protected Endpoints

Apply the same pattern to all endpoints that require authentication:

**Filesystem Endpoints:**
- `fs_ls` → operation: `"fs_ls"`, provide `path`
- `fs_read` → operation: `"fs_read"`, provide `path`
- `fs_write` → operation: `"fs_write"`, provide `path`
- `fs_mkdir` → operation: `"fs_mkdir"`, provide `path`
- `fs_rm` → operation: `"fs_rm"`, provide `path`

**Exec Endpoint:**
- `exec` → operation: `"exec"`, provide `command`

**Batch Endpoint:**
- For first item: `skip_rate_limit=True`
- For subsequent items: `skip_rate_limit=False`

---

## Example: Complete Integration for fs_read

```python
@app.get("/fs/read")
def fs_read(path: str, authorization: Optional[str] = Header(None)):
    # Enhanced security check
    if SECURITY_ENHANCED:
        target_path = _resolve_path(path)
        token_info = require_auth_and_permission(
            authorization=authorization,
            operation="fs_read",
            path=target_path
        )
        token_fp = rate_limiter.get_token_fingerprint(token_info.token)
    else:
        token_fp = _require_auth(authorization)
        target_path = _resolve_path(path)
    
    # Original logic continues...
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        text = target_path.read_text(encoding="utf-8")
        data = {"path": str(target_path), "content": text}
        
        _log_event("fs_read", token=token_fp, path=str(target_path), 
                  status="ok", mode="text", length=len(text))
        
        return data
    except UnicodeDecodeError:
        # Binary file handling...
        pass
```

---

## Example: Complete Integration for exec

```python
@app.post("/exec")
def exec_cmd(body: ExecBody, authorization: Optional[str] = Header(None)):
    # Enhanced security check
    if SECURITY_ENHANCED:
        cmd = list(body.cmd)
        if body.sudo:
            cmd = ["sudo"] + cmd
        
        token_info = require_auth_and_permission(
            authorization=authorization,
            operation="exec",
            command=cmd
        )
        token_fp = rate_limiter.get_token_fingerprint(token_info.token)
    else:
        token_fp = _require_auth(authorization)
        cmd = list(body.cmd)
        if body.sudo:
            if not ALLOW_SUDO:
                raise HTTPException(status_code=403, 
                                  detail="Sudo not allowed (set ALLOW_SUDO=1)")
            cmd = ["sudo"] + cmd
    
    # Original logic continues...
    cwd = _resolve_path(body.cwd) if body.cwd else BASE_DIR
    
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=body.timeout or 300,
            text=True,
        )
    except subprocess.TimeoutExpired:
        _log_event("exec", token=token_fp, status="timeout", 
                  cmd=cmd, cwd=str(cwd), timeout=body.timeout or 300)
        raise HTTPException(status_code=504, detail="Command timed out")
    
    rc = completed.returncode
    _log_event("exec", token=token_fp, status="ok", cmd=cmd, cwd=str(cwd), rc=rc)
    
    return {
        "cmd": cmd,
        "cwd": str(cwd),
        "rc": rc,
        "stdout": completed.stdout,
        "stderr": completed.stderr
    }
```

---

## Testing the Integration

### 1. Start the Server

```bash
cd ~/Desktop/Trapdoor
python3 control_panel.py
# Select option 1 to start
```

### 2. Test with Migrated Token

```bash
# Get your token from config/tokens.json or use existing AUTH_TOKEN
TOKEN="your_token_here"

# Test health (no auth required)
curl https://your-tunnel-url/health

# Test fs_ls (requires 'read' scope)
curl -H "Authorization: Bearer $TOKEN" \
     "https://your-tunnel-url/fs/ls?path=/"

# Test fs_write (requires 'write' scope)
curl -X POST https://your-tunnel-url/fs/write \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"path":"/tmp/test.txt","content":"Hello World","mode":"write"}'
```

### 3. Test Scoped Token

Create a read-only token:

```python
from security import TokenManager
tm = TokenManager()
token_info = tm.create_token(
    name="Test Read-Only",
    scopes=["read"],
    path_allowlist=["/tmp"],
    expires_in_days=1
)
print(f"Token: {token_info.token}")
```

Test with the new token:

```bash
TOKEN="newly_created_token"

# This should work (read operation)
curl -H "Authorization: Bearer $TOKEN" \
     "https://your-tunnel-url/fs/ls?path=/tmp"

# This should fail (write not in scope)
curl -X POST https://your-tunnel-url/fs/write \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"path":"/tmp/test.txt","content":"fail"}'
```

### 4. Test Approval Workflow

List pending approvals (requires admin token):

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     https://your-tunnel-url/approval/pending
```

Approve an operation:

```bash
curl -X POST "https://your-tunnel-url/approval/{request_id}/approve" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 5. Test Token Management

List all tokens:

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     https://your-tunnel-url/tokens/list
```

Rotate a token:

```bash
curl -X POST "https://your-tunnel-url/tokens/token_abc123/rotate" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Configuration Examples

### Example 1: Read-Only Monitoring Bot

`config/tokens.json`:
```json
{
  "tokens": [
    {
      "token_id": "monitor_bot",
      "name": "System Monitor",
      "token": "abc123...",
      "scopes": ["read"],
      "path_allowlist": ["/var/log", "/tmp"],
      "path_denylist": [],
      "rate_limits": {
        "requests_per_minute": 300,
        "requests_per_hour": 10000
      },
      "created": "2025-10-28T00:00:00",
      "enabled": true
    }
  ]
}
```

### Example 2: Deploy Agent with Approval

```json
{
  "token_id": "deploy_agent",
  "name": "CI/CD Deployer",
  "token": "def456...",
  "scopes": ["read", "write", "exec"],
  "path_allowlist": ["/home/app"],
  "command_allowlist": ["git", "npm", "node", "systemctl restart"],
  "require_approval": ["fs_rm"],
  "rate_limits": {
    "requests_per_minute": 100
  },
  "operation_limits": {
    "exec": {"requests_per_minute": 50}
  },
  "created": "2025-10-28T00:00:00",
  "expires": "2025-12-31T23:59:59",
  "enabled": true
}
```

### Example 3: Admin Token

```json
{
  "token_id": "admin_user",
  "name": "Administrator",
  "token": "ghi789...",
  "scopes": ["admin"],
  "created": "2025-10-28T00:00:00",
  "expires": "2026-10-28T00:00:00",
  "enabled": true
}
```

---

## Backward Compatibility

### Fallback Behavior

If `config/tokens.json` doesn't exist and auto-migration fails:
- Server falls back to legacy `AUTH_TOKEN` system
- All endpoints work as before
- No scoped permissions
- Basic rate limiting only

### Migration Path

1. **Start with auto-migration:**
   - Existing tokens automatically migrated with `admin` scope
   - No breaking changes
   - Everything works as before

2. **Gradually add scoped tokens:**
   - Create new tokens with specific scopes
   - Test with non-critical agents
   - Monitor audit logs

3. **Phase out admin tokens:**
   - Replace admin tokens with scoped tokens
   - Add path/command restrictions
   - Enable approval workflows

---

## Troubleshooting

### "Security system not initialized"

Make sure you called `setup_security()` at startup:

```python
token_manager, rate_limiter, approval_queue = setup_security()
```

### "Token lacks 'read' scope"

The token doesn't have the required scope. Update `config/tokens.json`:

```json
{
  "scopes": ["read", "write"]
}
```

Then restart the server.

### "Path not allowed"

The path is not in the token's allowlist or is in the denylist. Update the token:

```json
{
  "path_allowlist": ["/home/user", "/tmp"],
  "path_denylist": []
}
```

### "Rate limit exceeded"

Increase the token's rate limits:

```json
{
  "rate_limits": {
    "requests_per_minute": 200,
    "requests_per_hour": 5000
  }
}
```

---

## Security Best Practices

### 1. Use Scoped Tokens

❌ Don't: Grant `admin` scope to all tokens  
✅ Do: Use minimal scopes needed for each use case

### 2. Set Expiration Dates

❌ Don't: Create tokens without expiration  
✅ Do: Set reasonable expiration (90-365 days)

### 3. Use Path Restrictions

❌ Don't: Allow access to entire filesystem  
✅ Do: Restrict to specific directories

### 4. Enable Approval for Destructive Ops

❌ Don't: Allow `fs_rm` without approval  
✅ Do: Require approval for destructive operations

### 5. Monitor Audit Logs

❌ Don't: Ignore audit logs  
✅ Do: Review logs regularly for suspicious activity

### 6. Rotate Tokens Regularly

❌ Don't: Use same token forever  
✅ Do: Rotate tokens every 90 days

---

## Next Steps

1. ✅ Complete integration following this guide
2. ✅ Test with existing tokens (backward compatibility)
3. ✅ Create scoped tokens for different use cases
4. ✅ Enable approval workflows for sensitive operations
5. ✅ Monitor audit logs for permission denials
6. ✅ Update client documentation with new token format

---

**Integration Complete!** 🎉

Your Trapdoor instance now has:
- ✅ Scoped token permissions
- ✅ Path and command restrictions
- ✅ Token expiration and rotation
- ✅ Approval workflows
- ✅ Enhanced rate limiting
- ✅ Backward compatibility

For questions or issues, refer to:
- `SECURITY_ANALYSIS.md` - Technical details
- `SECURITY_ENHANCEMENT_DESIGN.md` - Architecture
- `security.py` - Implementation
- `security_integration.py` - Integration helpers
