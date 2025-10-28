"""
Security Integration Module

This module provides a drop-in replacement for the authentication
and permission checking in local_agent_server.py

Usage in local_agent_server.py:
    from security_integration import setup_security, require_auth_and_permission
    
    # At startup
    token_manager, rate_limiter, approval_queue = setup_security()
    
    # In endpoints, replace _require_auth() with:
    token_info = require_auth_and_permission(
        authorization=authorization,
        operation="fs_read",
        path=path
    )
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple
from fastapi import Header

from security import (
    TokenManager,
    RateLimiter,
    ApprovalQueue,
    TokenInfo,
    PermissionError,
    ApprovalRequiredError,
    migrate_from_env
)


# ==================== Global Instances ====================

_token_manager: Optional[TokenManager] = None
_rate_limiter: Optional[RateLimiter] = None
_approval_queue: Optional[ApprovalQueue] = None


# ==================== Setup ====================

def setup_security(
    config_path: Optional[Path] = None,
    auto_migrate: bool = True
) -> Tuple[TokenManager, RateLimiter, ApprovalQueue]:
    """
    Initialize security system
    
    Args:
        config_path: Path to tokens.json (default: config/tokens.json)
        auto_migrate: Automatically migrate from AUTH_TOKEN if tokens.json doesn't exist
    
    Returns:
        (TokenManager, RateLimiter, ApprovalQueue)
    """
    global _token_manager, _rate_limiter, _approval_queue
    
    config_path = config_path or Path("config/tokens.json")
    
    # Auto-migrate if needed
    if auto_migrate and not config_path.exists():
        auth_token = os.getenv("AUTH_TOKEN")
        auth_token_file = os.getenv("AUTH_TOKEN_FILE")
        
        if auth_token or auth_token_file:
            print("🔄 Migrating from AUTH_TOKEN to tokens.json...")
            migrate_from_env(auth_token, auth_token_file, config_path)
            print("✅ Migration complete")
    
    # Initialize components
    _token_manager = TokenManager(config_path)
    _rate_limiter = RateLimiter()
    _approval_queue = ApprovalQueue()
    
    print(f"🔐 Security system initialized with {len(_token_manager.tokens)} tokens")
    
    return _token_manager, _rate_limiter, _approval_queue


# ==================== Auth & Permission Checking ====================

def require_auth_and_permission(
    authorization: Optional[str],
    operation: str,
    path: Optional[Path] = None,
    command: Optional[List[str]] = None,
    skip_rate_limit: bool = False
) -> TokenInfo:
    """
    Combined authentication and permission checking
    
    This is a drop-in replacement for _require_auth() that adds:
    - Scoped permission checking
    - Path/command validation
    - Per-operation rate limiting
    - Approval workflow integration
    
    Args:
        authorization: Authorization header (Bearer token)
        operation: Operation being performed (fs_read, fs_write, exec, etc.)
        path: Path being accessed (for filesystem operations)
        command: Command being executed (for exec operations)
        skip_rate_limit: Skip rate limiting (for first item in batch)
    
    Returns:
        TokenInfo object
    
    Raises:
        HTTPException: 401 (auth failure), 403 (permission denied), 429 (rate limit)
        ApprovalRequiredError: Operation requires approval
    """
    if not _token_manager:
        raise RuntimeError("Security system not initialized. Call setup_security() first.")
    
    # Extract token from header
    if not authorization or not authorization.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")
    
    token = authorization.split(" ", 1)[1]
    
    # Validate token and check expiration
    token_info = _token_manager.validate_token(token)
    
    # Check permissions
    _token_manager.check_permission(
        token_info,
        operation,
        path=path,
        command=command
    )
    
    # Check if approval required
    if operation in token_info.require_approval or operation in _token_manager.require_approval_operations:
        # Request approval
        request_id = _approval_queue.request_approval(
            operation=operation,
            details={
                "token_name": token_info.name,
                "path": str(path) if path else None,
                "command": command,
                "timestamp": time.time()
            }
        )
        
        # Wait for approval (30 second timeout)
        if not _approval_queue.check_approval(request_id, timeout=30):
            raise PermissionError(f"Approval denied or timed out for {operation}")
    
    # Rate limiting
    if not skip_rate_limit and _rate_limiter:
        token_fp = _rate_limiter.get_token_fingerprint(token)
        
        # Check token-level rate limits
        _rate_limiter.check_and_record(
            token_fp,
            token_info.rate_limits
        )
        
        # Check operation-specific rate limits
        if operation in token_info.operation_limits:
            _rate_limiter.check_and_record(
                token_fp,
                token_info.operation_limits[operation],
                operation=operation
            )
    
    return token_info


# ==================== Backward Compatibility ====================

def legacy_require_auth(authorization: Optional[str]) -> Optional[str]:
    """
    Backward-compatible version of _require_auth()
    
    Returns token fingerprint (for logging) instead of TokenInfo.
    This maintains compatibility with existing code.
    """
    if not _token_manager or not _token_manager.tokens:
        # No tokens configured - fall back to legacy behavior (no auth)
        return None
    
    try:
        token_info = require_auth_and_permission(
            authorization=authorization,
            operation="legacy",  # Generic operation
            skip_rate_limit=False
        )
        return _rate_limiter.get_token_fingerprint(token_info.token) if _rate_limiter else None
    except Exception:
        raise


# ==================== Approval Management ====================

def get_approval_queue() -> ApprovalQueue:
    """Get the global approval queue instance"""
    if not _approval_queue:
        raise RuntimeError("Security system not initialized")
    return _approval_queue


def get_token_manager() -> TokenManager:
    """Get the global token manager instance"""
    if not _token_manager:
        raise RuntimeError("Security system not initialized")
    return _token_manager


# ==================== Utility Functions ====================

import time

def log_security_event(
    token_info: TokenInfo,
    operation: str,
    status: str,
    **kwargs
) -> None:
    """Log security-relevant events"""
    # This can be extended to integrate with existing _log_event() function
    pass
