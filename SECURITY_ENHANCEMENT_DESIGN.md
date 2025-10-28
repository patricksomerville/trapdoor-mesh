# Trapdoor Security Enhancement Design

**Date:** October 28, 2025  
**Status:** Design Phase  
**Goal:** Enhanced security with scoped permissions, multi-token system, and better controls

---

## 1. Token System Architecture

### 1.1 Token Structure

```json
{
  "token_id": "token_abc123",
  "name": "Genspark Production",
  "token": "90ac04027a0b4aba685dcae29eeed91a",
  "created": "2025-10-28T00:00:00Z",
  "expires": "2026-10-28T00:00:00Z",
  "last_used": "2025-10-28T12:34:56Z",
  "enabled": true,
  "scopes": ["read", "write", "exec"],
  "rate_limits": {
    "requests_per_minute": 120,
    "requests_per_hour": 1000,
    "requests_per_day": 10000
  },
  "path_rules": {
    "allowlist": ["/home/user/projects", "/tmp"],
    "denylist": ["/etc", "~/.ssh", "/var"]
  },
  "command_rules": {
    "allowlist": ["git", "npm", "python3", "node"],
    "denylist": ["rm -rf /", "dd", "mkfs"]
  },
  "require_approval": ["fs_rm", "exec"],
  "metadata": {
    "owner": "team@example.com",
    "purpose": "Production deployment"
  }
}
```

### 1.2 Scope Definitions

**Read Scopes:**
- `read` - Read files, list directories
- `read:sensitive` - Read sensitive files (requires explicit allowlist)

**Write Scopes:**
- `write` - Write/append files, create directories
- `write:destructive` - Delete files/directories

**Exec Scopes:**
- `exec` - Execute commands from allowlist
- `exec:sudo` - Execute with sudo (requires ALLOW_SUDO=1 globally)

**Admin Scopes:**
- `admin` - Bypass all restrictions (equivalent to current behavior)

### 1.3 Token Storage

**File:** `config/tokens.json`

```json
{
  "tokens": [
    {
      "token_id": "default",
      "name": "Default Token (Backward Compat)",
      "token": "...",
      "scopes": ["admin"]
    },
    {
      "token_id": "readonly_agent",
      "name": "Read-Only Agent",
      "token": "...",
      "scopes": ["read"],
      "path_rules": {
        "allowlist": ["/home/user/projects"]
      }
    }
  ],
  "global_rules": {
    "default_rate_limit": {
      "requests_per_minute": 120
    },
    "global_denylist": ["/etc/shadow", "/etc/passwd", "~/.ssh"],
    "require_approval_operations": ["fs_rm", "exec:sudo"]
  }
}
```

---

## 2. TokenManager Class

### 2.1 Core Methods

```python
class TokenManager:
    def __init__(self, config_path: Path):
        """Load tokens from config file"""
        
    def validate_token(self, token: str) -> TokenInfo:
        """Validate token and return metadata"""
        
    def check_permission(self, token_info: TokenInfo, 
                        operation: str, 
                        path: Optional[Path] = None,
                        command: Optional[List[str]] = None) -> bool:
        """Check if token has permission for operation"""
        
    def enforce_rate_limit(self, token_info: TokenInfo) -> None:
        """Enforce per-token rate limits"""
        
    def record_usage(self, token_info: TokenInfo, operation: str) -> None:
        """Update last_used timestamp"""
        
    def is_expired(self, token_info: TokenInfo) -> bool:
        """Check if token is expired"""
        
    def rotate_token(self, token_id: str) -> str:
        """Generate new token for given ID"""
        
class TokenInfo:
    token_id: str
    name: str
    token: str
    scopes: Set[str]
    path_allowlist: Optional[List[str]]
    path_denylist: Optional[List[str]]
    command_allowlist: Optional[List[str]]
    command_denylist: Optional[List[str]]
    rate_limits: Dict[str, int]
    require_approval: Set[str]
    created: datetime
    expires: Optional[datetime]
    last_used: Optional[datetime]
    enabled: bool
```

---

## 3. Permission Checking Logic

### 3.1 Operation Permission Check

```python
def check_permission(token_info: TokenInfo, operation: str, 
                    path: Optional[Path] = None,
                    command: Optional[List[str]] = None) -> bool:
    # Admin scope bypasses all checks
    if "admin" in token_info.scopes:
        return True
    
    # Check operation scope
    if operation == "fs_read":
        if "read" not in token_info.scopes:
            raise PermissionError("Token lacks 'read' scope")
    
    elif operation == "fs_write":
        if "write" not in token_info.scopes:
            raise PermissionError("Token lacks 'write' scope")
    
    elif operation == "fs_rm":
        if "write:destructive" not in token_info.scopes:
            raise PermissionError("Token lacks 'write:destructive' scope")
    
    elif operation == "exec":
        if "exec" not in token_info.scopes:
            raise PermissionError("Token lacks 'exec' scope")
    
    # Check path rules
    if path:
        if not check_path_allowed(token_info, path):
            raise PermissionError(f"Path not allowed: {path}")
    
    # Check command rules
    if command:
        if not check_command_allowed(token_info, command):
            raise PermissionError(f"Command not allowed: {command[0]}")
    
    # Check if approval required
    if operation in token_info.require_approval:
        raise ApprovalRequiredError(f"Operation '{operation}' requires approval")
    
    return True
```

### 3.2 Path Checking

```python
def check_path_allowed(token_info: TokenInfo, path: Path) -> bool:
    path_str = str(path.resolve())
    
    # Check global denylist first
    for denied in GLOBAL_DENYLIST:
        denied_path = Path(denied).expanduser().resolve()
        if path_str.startswith(str(denied_path)):
            return False
    
    # Check token-specific denylist
    if token_info.path_denylist:
        for denied in token_info.path_denylist:
            denied_path = Path(denied).expanduser().resolve()
            if path_str.startswith(str(denied_path)):
                return False
    
    # If allowlist exists, path must be in it
    if token_info.path_allowlist:
        for allowed in token_info.path_allowlist:
            allowed_path = Path(allowed).expanduser().resolve()
            if path_str.startswith(str(allowed_path)):
                return True
        return False  # Not in allowlist
    
    return True  # No allowlist means all paths allowed (minus denylists)
```

### 3.3 Command Checking

```python
def check_command_allowed(token_info: TokenInfo, command: List[str]) -> bool:
    cmd_name = Path(command[0]).name  # Handle absolute paths
    
    # Check denylist first
    if token_info.command_denylist:
        for denied in token_info.command_denylist:
            if cmd_name == denied or " ".join(command).startswith(denied):
                return False
    
    # If allowlist exists, command must be in it
    if token_info.command_allowlist:
        for allowed in token_info.command_allowlist:
            if cmd_name == allowed:
                return True
        return False  # Not in allowlist
    
    return True  # No allowlist means all commands allowed (minus denylists)
```

---

## 4. Rate Limiting Enhancements

### 4.1 Multi-Level Rate Limits

```python
class RateLimiter:
    def __init__(self):
        self.per_minute: Dict[str, deque] = {}
        self.per_hour: Dict[str, deque] = {}
        self.per_day: Dict[str, deque] = {}
        self.lock = threading.Lock()
    
    def check_and_record(self, token_fp: str, limits: Dict[str, int]) -> None:
        """Check all rate limits and record usage"""
        now = time.time()
        
        with self.lock:
            # Per-minute check
            if "requests_per_minute" in limits:
                self._check_window(
                    self.per_minute, token_fp, now, 60, 
                    limits["requests_per_minute"]
                )
            
            # Per-hour check
            if "requests_per_hour" in limits:
                self._check_window(
                    self.per_hour, token_fp, now, 3600,
                    limits["requests_per_hour"]
                )
            
            # Per-day check
            if "requests_per_day" in limits:
                self._check_window(
                    self.per_day, token_fp, now, 86400,
                    limits["requests_per_day"]
                )
    
    def _check_window(self, storage: Dict, key: str, now: float,
                     window: int, limit: int) -> None:
        history = storage.setdefault(key, deque())
        cutoff = now - window
        
        # Remove old entries
        while history and history[0] < cutoff:
            history.popleft()
        
        if len(history) >= limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded: {limit} requests per {window}s"
            )
        
        history.append(now)
```

### 4.2 Per-Operation Rate Limits

```python
# In TokenInfo
operation_limits: Dict[str, Dict[str, int]] = {
    "fs_read": {"requests_per_minute": 200},
    "fs_write": {"requests_per_minute": 50},
    "fs_rm": {"requests_per_minute": 10},
    "exec": {"requests_per_minute": 30}
}
```

---

## 5. Approval Mode

### 5.1 Approval Queue System

```python
class ApprovalQueue:
    def __init__(self):
        self.pending: Dict[str, PendingOperation] = {}
        self.lock = threading.Lock()
    
    def request_approval(self, operation: str, details: Dict) -> str:
        """Queue operation for approval, return request_id"""
        request_id = secrets.token_hex(8)
        
        with self.lock:
            self.pending[request_id] = PendingOperation(
                request_id=request_id,
                operation=operation,
                details=details,
                timestamp=time.time(),
                status="pending"
            )
        
        return request_id
    
    def check_approval(self, request_id: str, timeout: int = 30) -> bool:
        """Wait for approval decision"""
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                if request_id not in self.pending:
                    return False
                
                op = self.pending[request_id]
                if op.status == "approved":
                    del self.pending[request_id]
                    return True
                elif op.status == "denied":
                    del self.pending[request_id]
                    return False
            
            time.sleep(0.5)
        
        # Timeout
        with self.lock:
            if request_id in self.pending:
                del self.pending[request_id]
        return False
    
    def approve(self, request_id: str) -> None:
        """Approve a pending operation"""
        with self.lock:
            if request_id in self.pending:
                self.pending[request_id].status = "approved"
    
    def deny(self, request_id: str) -> None:
        """Deny a pending operation"""
        with self.lock:
            if request_id in self.pending:
                self.pending[request_id].status = "denied"
```

### 5.2 Approval Endpoint

```python
@app.get("/approval/pending")
def list_pending_approvals(authorization: Optional[str] = Header(None)):
    """List pending approval requests (admin only)"""
    token_info = token_manager.validate_token(authorization)
    if "admin" not in token_info.scopes:
        raise HTTPException(403, "Admin scope required")
    
    return {"pending": list(approval_queue.pending.values())}

@app.post("/approval/{request_id}/approve")
def approve_operation(request_id: str, authorization: Optional[str] = Header(None)):
    """Approve a pending operation (admin only)"""
    token_info = token_manager.validate_token(authorization)
    if "admin" not in token_info.scopes:
        raise HTTPException(403, "Admin scope required")
    
    approval_queue.approve(request_id)
    return {"status": "approved"}

@app.post("/approval/{request_id}/deny")
def deny_operation(request_id: str, authorization: Optional[str] = Header(None)):
    """Deny a pending operation (admin only)"""
    token_info = token_manager.validate_token(authorization)
    if "admin" not in token_info.scopes:
        raise HTTPException(403, "Admin scope required")
    
    approval_queue.deny(request_id)
    return {"status": "denied"}
```

---

## 6. Implementation Plan

### Phase 1: Core Token System (Week 1)
- [ ] Create `TokenManager` class
- [ ] Create `TokenInfo` dataclass
- [ ] Implement token loading from `config/tokens.json`
- [ ] Add backward compatibility with existing AUTH_TOKEN
- [ ] Update `_require_auth()` to use TokenManager
- [ ] Add token expiration checks

### Phase 2: Scoped Permissions (Week 1)
- [ ] Implement scope checking logic
- [ ] Add path allowlist/denylist validation
- [ ] Add command allowlist/denylist validation
- [ ] Update all endpoints to check permissions
- [ ] Add detailed error messages for permission failures

### Phase 3: Enhanced Rate Limiting (Week 2)
- [ ] Create `RateLimiter` class with multi-window support
- [ ] Implement per-operation rate limits
- [ ] Add per-token daily/hourly quotas
- [ ] Update endpoints to use new rate limiter

### Phase 4: Approval System (Week 2)
- [ ] Create `ApprovalQueue` class
- [ ] Add approval endpoints (list, approve, deny)
- [ ] Integrate approval checks into destructive operations
- [ ] Add CLI command for managing approvals

### Phase 5: Testing & Migration (Week 3)
- [ ] Write unit tests for TokenManager
- [ ] Write integration tests for permission checks
- [ ] Create migration script for existing tokens
- [ ] Update documentation
- [ ] Create example token configurations

---

## 7. Backward Compatibility

### 7.1 Migration Path

**Existing Setup:**
```bash
AUTH_TOKEN=abc123
```

**Migrated Setup:**
```json
{
  "tokens": [
    {
      "token_id": "legacy_token",
      "name": "Migrated from AUTH_TOKEN",
      "token": "abc123",
      "scopes": ["admin"],
      "created": "2025-10-28T00:00:00Z"
    }
  ]
}
```

### 7.2 Auto-Migration

On startup, if `config/tokens.json` doesn't exist but `AUTH_TOKEN` is set:
1. Create `config/tokens.json`
2. Import all tokens from `AUTH_TOKEN` and `AUTH_TOKEN_FILE`
3. Grant them `admin` scope for backward compatibility
4. Log migration completion

---

## 8. Configuration Examples

### 8.1 Read-Only Agent

```json
{
  "token_id": "readonly_bot",
  "name": "Read-Only Bot",
  "token": "...",
  "scopes": ["read"],
  "path_rules": {
    "allowlist": ["/home/user/projects", "/tmp"],
    "denylist": ["~/.ssh", "~/.aws"]
  },
  "rate_limits": {
    "requests_per_minute": 200,
    "requests_per_hour": 5000
  }
}
```

### 8.2 Deploy Agent

```json
{
  "token_id": "deploy_agent",
  "name": "Deployment Agent",
  "token": "...",
  "scopes": ["read", "write", "exec"],
  "path_rules": {
    "allowlist": ["/home/user/app"],
    "denylist": []
  },
  "command_rules": {
    "allowlist": ["git", "npm", "node", "pm2", "systemctl"],
    "denylist": ["rm -rf /"]
  },
  "require_approval": ["fs_rm"],
  "rate_limits": {
    "requests_per_minute": 100,
    "requests_per_hour": 2000
  },
  "expires": "2025-12-31T23:59:59Z"
}
```

### 8.3 Admin Token

```json
{
  "token_id": "admin",
  "name": "Full Admin Access",
  "token": "...",
  "scopes": ["admin"],
  "expires": "2026-01-01T00:00:00Z"
}
```

---

## 9. Security Benefits

### Before:
❌ Single token = full access  
❌ No path restrictions  
❌ No command restrictions  
❌ No token expiration  
❌ No operation-specific limits  
❌ No approval workflows  

### After:
✅ Multi-token system with scoped permissions  
✅ Path allowlist/denylist per token  
✅ Command allowlist/denylist per token  
✅ Token expiration and rotation  
✅ Per-operation rate limits  
✅ Approval workflows for destructive ops  
✅ Detailed audit logging with permissions  
✅ Backward compatible migration  

---

## 10. Testing Strategy

### Unit Tests
- Token validation and expiration
- Scope checking logic
- Path/command allow/deny rules
- Rate limiting windows
- Approval queue operations

### Integration Tests
- Full request flow with scoped tokens
- Permission denial scenarios
- Rate limit enforcement
- Approval workflow end-to-end

### Security Tests
- Path traversal attempts
- Command injection attempts
- Rate limit bypass attempts
- Token reuse after expiration
- Privilege escalation attempts

---

**End of Design Document**
