"""
Trapdoor Enhanced Security Module

Provides:
- Multi-token system with scoped permissions
- Path and command allowlist/denylist
- Token expiration and rotation
- Enhanced rate limiting
- Approval workflows
"""

import json
import hashlib
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from fastapi import HTTPException


# ==================== Exceptions ====================

class PermissionError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


class RateLimitExceeded(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=429, detail=detail)


class ApprovalRequiredError(HTTPException):
    def __init__(self, detail: str, request_id: str):
        super().__init__(
            status_code=202,
            detail=f"{detail}. Approval request ID: {request_id}"
        )


class TokenExpiredError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)


# ==================== Data Classes ====================

@dataclass
class TokenInfo:
    """Structured token information with permissions"""
    token_id: str
    name: str
    token: str
    scopes: Set[str]
    created: datetime
    enabled: bool = True
    
    # Optional fields
    expires: Optional[datetime] = None
    last_used: Optional[datetime] = None
    
    # Path rules
    path_allowlist: Optional[List[str]] = None
    path_denylist: Optional[List[str]] = None
    
    # Command rules
    command_allowlist: Optional[List[str]] = None
    command_denylist: Optional[List[str]] = None
    
    # Rate limits
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "requests_per_minute": 120
    })
    
    # Operation-specific rate limits
    operation_limits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Operations requiring approval
    require_approval: Set[str] = field(default_factory=set)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (for storage)"""
        return {
            "token_id": self.token_id,
            "name": self.name,
            "token": self.token,
            "scopes": list(self.scopes),
            "created": self.created.isoformat(),
            "expires": self.expires.isoformat() if self.expires else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "enabled": self.enabled,
            "path_allowlist": self.path_allowlist,
            "path_denylist": self.path_denylist,
            "command_allowlist": self.command_allowlist,
            "command_denylist": self.command_denylist,
            "rate_limits": self.rate_limits,
            "operation_limits": self.operation_limits,
            "require_approval": list(self.require_approval),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenInfo":
        """Deserialize from dictionary"""
        return cls(
            token_id=data["token_id"],
            name=data["name"],
            token=data["token"],
            scopes=set(data.get("scopes", [])),
            created=datetime.fromisoformat(data["created"]),
            expires=datetime.fromisoformat(data["expires"]) if data.get("expires") else None,
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            enabled=data.get("enabled", True),
            path_allowlist=data.get("path_allowlist"),
            path_denylist=data.get("path_denylist"),
            command_allowlist=data.get("command_allowlist"),
            command_denylist=data.get("command_denylist"),
            rate_limits=data.get("rate_limits", {"requests_per_minute": 120}),
            operation_limits=data.get("operation_limits", {}),
            require_approval=set(data.get("require_approval", [])),
            metadata=data.get("metadata", {})
        )


@dataclass
class PendingOperation:
    """Pending operation awaiting approval"""
    request_id: str
    operation: str
    details: Dict[str, Any]
    timestamp: float
    status: str = "pending"  # pending, approved, denied


# ==================== Token Manager ====================

class TokenManager:
    """Manages token validation, permissions, and operations"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/tokens.json")
        self.tokens: Dict[str, TokenInfo] = {}
        self.token_lookup: Dict[str, str] = {}  # token -> token_id
        self.lock = threading.RLock()
        
        # Global rules
        self.global_denylist: List[str] = []
        self.require_approval_operations: Set[str] = set()
        
        self._load_tokens()
    
    def _load_tokens(self) -> None:
        """Load tokens from config file"""
        if not self.config_path.exists():
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Load global rules
            global_rules = config.get("global_rules", {})
            self.global_denylist = global_rules.get("global_denylist", [])
            self.require_approval_operations = set(
                global_rules.get("require_approval_operations", [])
            )
            
            # Load tokens
            for token_data in config.get("tokens", []):
                token_info = TokenInfo.from_dict(token_data)
                self.tokens[token_info.token_id] = token_info
                self.token_lookup[token_info.token] = token_info.token_id
        
        except Exception as e:
            print(f"Error loading tokens: {e}")
    
    def save_tokens(self) -> None:
        """Save tokens to config file"""
        with self.lock:
            config = {
                "tokens": [t.to_dict() for t in self.tokens.values()],
                "global_rules": {
                    "global_denylist": self.global_denylist,
                    "require_approval_operations": list(self.require_approval_operations)
                }
            }
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
    
    def validate_token(self, token: str) -> TokenInfo:
        """Validate token and return TokenInfo"""
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        
        token_id = self.token_lookup.get(token)
        if not token_id:
            raise HTTPException(status_code=403, detail="Invalid token")
        
        token_info = self.tokens[token_id]
        
        # Check if token is enabled
        if not token_info.enabled:
            raise HTTPException(status_code=403, detail="Token is disabled")
        
        # Check if token is expired
        if token_info.expires and datetime.now() > token_info.expires:
            raise TokenExpiredError(f"Token expired on {token_info.expires.isoformat()}")
        
        # Update last used timestamp
        with self.lock:
            token_info.last_used = datetime.now()
            self.save_tokens()
        
        return token_info
    
    def check_permission(
        self,
        token_info: TokenInfo,
        operation: str,
        path: Optional[Path] = None,
        command: Optional[List[str]] = None
    ) -> bool:
        """Check if token has permission for operation"""
        
        # Admin scope bypasses all checks
        if "admin" in token_info.scopes:
            return True
        
        # Check operation scope
        if operation in ["fs_ls", "fs_read"]:
            if "read" not in token_info.scopes:
                raise PermissionError(f"Token '{token_info.name}' lacks 'read' scope for {operation}")
        
        elif operation in ["fs_write", "fs_mkdir"]:
            if "write" not in token_info.scopes:
                raise PermissionError(f"Token '{token_info.name}' lacks 'write' scope for {operation}")
        
        elif operation == "fs_rm":
            if "write:destructive" not in token_info.scopes:
                raise PermissionError(f"Token '{token_info.name}' lacks 'write:destructive' scope for {operation}")
        
        elif operation == "exec":
            if "exec" not in token_info.scopes:
                raise PermissionError(f"Token '{token_info.name}' lacks 'exec' scope for {operation}")
            
            # Check for sudo
            if command and "sudo" in command:
                if "exec:sudo" not in token_info.scopes:
                    raise PermissionError(f"Token '{token_info.name}' lacks 'exec:sudo' scope")
        
        # Check path rules
        if path:
            if not self._check_path_allowed(token_info, path):
                raise PermissionError(f"Path not allowed: {path}")
        
        # Check command rules
        if command:
            if not self._check_command_allowed(token_info, command):
                raise PermissionError(f"Command not allowed: {command[0]}")
        
        return True
    
    def _check_path_allowed(self, token_info: TokenInfo, path: Path) -> bool:
        """Check if path is allowed for this token"""
        path_str = str(path.resolve())
        
        # Check global denylist first
        for denied in self.global_denylist:
            denied_path = str(Path(denied).expanduser().resolve())
            if path_str.startswith(denied_path):
                return False
        
        # Check token-specific denylist
        if token_info.path_denylist:
            for denied in token_info.path_denylist:
                denied_path = str(Path(denied).expanduser().resolve())
                if path_str.startswith(denied_path):
                    return False
        
        # If allowlist exists, path must be in it
        if token_info.path_allowlist:
            for allowed in token_info.path_allowlist:
                allowed_path = str(Path(allowed).expanduser().resolve())
                if path_str.startswith(allowed_path):
                    return True
            return False  # Not in allowlist
        
        return True  # No allowlist means all paths allowed (minus denylists)
    
    def _check_command_allowed(self, token_info: TokenInfo, command: List[str]) -> bool:
        """Check if command is allowed for this token"""
        if not command:
            return False
        
        cmd_name = Path(command[0]).name  # Handle absolute paths
        full_cmd = " ".join(command)
        
        # Check denylist first
        if token_info.command_denylist:
            for denied in token_info.command_denylist:
                if cmd_name == denied or full_cmd.startswith(denied):
                    return False
        
        # If allowlist exists, command must be in it
        if token_info.command_allowlist:
            for allowed in token_info.command_allowlist:
                if cmd_name == allowed:
                    return True
            return False  # Not in allowlist
        
        return True  # No allowlist means all commands allowed (minus denylists)
    
    def rotate_token(self, token_id: str) -> str:
        """Generate new token for given ID"""
        if token_id not in self.tokens:
            raise ValueError(f"Token ID not found: {token_id}")
        
        with self.lock:
            old_token = self.tokens[token_id].token
            new_token = secrets.token_hex(16)
            
            # Update token
            self.tokens[token_id].token = new_token
            
            # Update lookup
            del self.token_lookup[old_token]
            self.token_lookup[new_token] = token_id
            
            self.save_tokens()
            
        return new_token
    
    def create_token(
        self,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
        **kwargs
    ) -> TokenInfo:
        """Create a new token"""
        token_id = f"token_{secrets.token_hex(8)}"
        token = secrets.token_hex(16)
        
        expires = None
        if expires_in_days:
            expires = datetime.now() + timedelta(days=expires_in_days)
        
        token_info = TokenInfo(
            token_id=token_id,
            name=name,
            token=token,
            scopes=set(scopes),
            created=datetime.now(),
            expires=expires,
            **kwargs
        )
        
        with self.lock:
            self.tokens[token_id] = token_info
            self.token_lookup[token] = token_id
            self.save_tokens()
        
        return token_info
    
    def disable_token(self, token_id: str) -> None:
        """Disable a token"""
        if token_id not in self.tokens:
            raise ValueError(f"Token ID not found: {token_id}")
        
        with self.lock:
            self.tokens[token_id].enabled = False
            self.save_tokens()
    
    def migrate_legacy_tokens(self, legacy_tokens: List[str]) -> None:
        """Migrate legacy tokens from AUTH_TOKEN to new system"""
        for token in legacy_tokens:
            if token in self.token_lookup:
                continue  # Already migrated
            
            self.create_token(
                name=f"Migrated Legacy Token",
                scopes=["admin"],  # Grant admin for backward compatibility
                token=token,  # Use existing token
                metadata={"migrated": True, "migration_date": datetime.now().isoformat()}
            )


# ==================== Rate Limiter ====================

class RateLimiter:
    """Multi-window rate limiter with per-operation limits"""
    
    def __init__(self):
        self.per_minute: Dict[str, deque] = {}
        self.per_hour: Dict[str, deque] = {}
        self.per_day: Dict[str, deque] = {}
        self.lock = threading.RLock()
    
    def check_and_record(
        self,
        token_fp: str,
        limits: Dict[str, int],
        operation: Optional[str] = None
    ) -> None:
        """Check all rate limits and record usage"""
        now = time.time()
        
        with self.lock:
            # Per-minute check
            if "requests_per_minute" in limits:
                self._check_window(
                    self.per_minute,
                    token_fp,
                    now,
                    60,
                    limits["requests_per_minute"],
                    operation
                )
            
            # Per-hour check
            if "requests_per_hour" in limits:
                self._check_window(
                    self.per_hour,
                    token_fp,
                    now,
                    3600,
                    limits["requests_per_hour"],
                    operation
                )
            
            # Per-day check
            if "requests_per_day" in limits:
                self._check_window(
                    self.per_day,
                    token_fp,
                    now,
                    86400,
                    limits["requests_per_day"],
                    operation
                )
    
    def _check_window(
        self,
        storage: Dict[str, deque],
        key: str,
        now: float,
        window: int,
        limit: int,
        operation: Optional[str] = None
    ) -> None:
        """Check rate limit for a specific window"""
        storage_key = f"{key}:{operation}" if operation else key
        history = storage.setdefault(storage_key, deque())
        cutoff = now - window
        
        # Remove old entries
        while history and history[0] < cutoff:
            history.popleft()
        
        if len(history) >= limit:
            window_desc = f"{window}s"
            if window == 60:
                window_desc = "minute"
            elif window == 3600:
                window_desc = "hour"
            elif window == 86400:
                window_desc = "day"
            
            op_desc = f" for {operation}" if operation else ""
            raise RateLimitExceeded(
                f"Rate limit exceeded: {limit} requests per {window_desc}{op_desc}"
            )
        
        history.append(now)
    
    def get_token_fingerprint(self, token: str) -> str:
        """Generate token fingerprint for rate limiting"""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


# ==================== Approval Queue ====================

class ApprovalQueue:
    """Queue system for operations requiring approval"""
    
    def __init__(self):
        self.pending: Dict[str, PendingOperation] = {}
        self.lock = threading.RLock()
    
    def request_approval(
        self,
        operation: str,
        details: Dict[str, Any]
    ) -> str:
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
        """Wait for approval decision (blocking)"""
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
        
        # Timeout - remove from queue
        with self.lock:
            if request_id in self.pending:
                del self.pending[request_id]
        
        return False
    
    def approve(self, request_id: str) -> bool:
        """Approve a pending operation"""
        with self.lock:
            if request_id in self.pending:
                self.pending[request_id].status = "approved"
                return True
        return False
    
    def deny(self, request_id: str) -> bool:
        """Deny a pending operation"""
        with self.lock:
            if request_id in self.pending:
                self.pending[request_id].status = "denied"
                return True
        return False
    
    def list_pending(self) -> List[Dict[str, Any]]:
        """List all pending approval requests"""
        with self.lock:
            return [
                {
                    "request_id": op.request_id,
                    "operation": op.operation,
                    "details": op.details,
                    "timestamp": op.timestamp,
                    "age_seconds": time.time() - op.timestamp
                }
                for op in self.pending.values()
            ]


# ==================== Migration Utilities ====================

def migrate_from_env(
    auth_token: Optional[str] = None,
    auth_token_file: Optional[str] = None,
    output_path: Optional[Path] = None
) -> None:
    """Migrate from AUTH_TOKEN environment to tokens.json"""
    tokens_to_migrate = []
    
    # Collect tokens from environment
    if auth_token:
        for t in auth_token.split(","):
            t = t.strip()
            if t:
                tokens_to_migrate.append(t)
    
    # Collect tokens from file
    if auth_token_file and Path(auth_token_file).exists():
        with open(auth_token_file, "r", encoding="utf-8") as f:
            for line in f:
                tok = line.strip()
                if tok:
                    tokens_to_migrate.append(tok)
    
    if not tokens_to_migrate:
        print("No tokens to migrate")
        return
    
    # Create token manager
    config_path = output_path or Path("config/tokens.json")
    manager = TokenManager(config_path)
    
    # Migrate each token
    for idx, token in enumerate(tokens_to_migrate, 1):
        token_id = f"migrated_{idx}"
        token_info = TokenInfo(
            token_id=token_id,
            name=f"Migrated Token #{idx}",
            token=token,
            scopes={"admin"},  # Grant admin for backward compatibility
            created=datetime.now(),
            metadata={
                "migrated": True,
                "migration_date": datetime.now().isoformat()
            }
        )
        
        manager.tokens[token_id] = token_info
        manager.token_lookup[token] = token_id
    
    manager.save_tokens()
    print(f"Migrated {len(tokens_to_migrate)} tokens to {config_path}")


# ==================== Example Configuration Generator ====================

def generate_example_config(output_path: Optional[Path] = None) -> None:
    """Generate example tokens.json configuration"""
    config = {
        "tokens": [
            {
                "token_id": "admin_token",
                "name": "Admin Token",
                "token": secrets.token_hex(16),
                "scopes": ["admin"],
                "created": datetime.now().isoformat(),
                "expires": (datetime.now() + timedelta(days=365)).isoformat(),
                "enabled": True,
                "metadata": {
                    "owner": "admin@example.com",
                    "purpose": "Full administrative access"
                }
            },
            {
                "token_id": "readonly_bot",
                "name": "Read-Only Bot",
                "token": secrets.token_hex(16),
                "scopes": ["read"],
                "created": datetime.now().isoformat(),
                "expires": (datetime.now() + timedelta(days=90)).isoformat(),
                "enabled": True,
                "path_allowlist": ["/home/user/projects", "/tmp"],
                "path_denylist": ["~/.ssh", "~/.aws"],
                "rate_limits": {
                    "requests_per_minute": 200,
                    "requests_per_hour": 5000
                },
                "metadata": {
                    "owner": "bot@example.com",
                    "purpose": "Read-only monitoring"
                }
            },
            {
                "token_id": "deploy_agent",
                "name": "Deployment Agent",
                "token": secrets.token_hex(16),
                "scopes": ["read", "write", "exec"],
                "created": datetime.now().isoformat(),
                "expires": (datetime.now() + timedelta(days=180)).isoformat(),
                "enabled": True,
                "path_allowlist": ["/home/user/app"],
                "command_allowlist": ["git", "npm", "node", "pm2", "systemctl"],
                "require_approval": ["fs_rm"],
                "rate_limits": {
                    "requests_per_minute": 100,
                    "requests_per_hour": 2000
                },
                "metadata": {
                    "owner": "deploy@example.com",
                    "purpose": "Automated deployment"
                }
            }
        ],
        "global_rules": {
            "global_denylist": [
                "/etc/shadow",
                "/etc/passwd",
                "~/.ssh",
                "~/.aws/credentials"
            ],
            "require_approval_operations": ["fs_rm", "exec:sudo"]
        }
    }
    
    output_path = output_path or Path("config/tokens.example.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"Generated example configuration at {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "generate":
            generate_example_config()
        elif sys.argv[1] == "migrate":
            import os
            migrate_from_env(
                auth_token=os.getenv("AUTH_TOKEN"),
                auth_token_file=os.getenv("AUTH_TOKEN_FILE")
            )
    else:
        print("Usage:")
        print("  python security.py generate  - Generate example config")
        print("  python security.py migrate   - Migrate from AUTH_TOKEN")
