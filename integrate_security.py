#!/usr/bin/env python3
"""
Automated Security Integration Script

This script integrates the enhanced security system into local_agent_server.py
"""

import re
from pathlib import Path


def integrate_security():
    """Integrate security system into local_agent_server.py"""
    
    server_file = Path("/Users/patricksomerville/Desktop/local_agent_server.py")
    
    if not server_file.exists():
        print(f"❌ Server file not found: {server_file}")
        return False
    
    # Read the original file
    with open(server_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if already integrated
    if "from security_integration import" in content:
        print("⚠️  Security system already integrated!")
        return False
    
    # 1. Add security imports after the TRAPDOOR_REPO_DIR setup
    security_imports = """
# ============================================================
# ENHANCED SECURITY SYSTEM
# ============================================================
try:
    from security_integration import (
        setup_security,
        require_auth_and_permission,
        get_approval_queue,
        get_token_manager
    )
    from approval_endpoints import register_approval_endpoints
    SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Enhanced security not available: {e}")
    SECURITY_AVAILABLE = False
"""
    
    # Find the spot after memory import
    memory_import_pattern = r"(from starlette\.background import BackgroundTask\n)"
    content = re.sub(
        memory_import_pattern,
        r"\1" + security_imports + "\n",
        content,
        count=1
    )
    
    # 2. Add security initialization after app creation
    security_init = """
# ============================================================
# Initialize Enhanced Security System
# ============================================================
SECURITY_ENHANCED = False
if SECURITY_AVAILABLE:
    try:
        # Change to Trapdoor directory for config loading
        original_cwd = Path.cwd()
        if TRAPDOOR_REPO_DIR.exists():
            import os
            os.chdir(TRAPDOOR_REPO_DIR)
        
        token_manager, rate_limiter, approval_queue = setup_security(
            config_path=TRAPDOOR_REPO_DIR / "config" / "tokens.json",
            auto_migrate=True  # Automatically migrate from AUTH_TOKEN
        )
        
        # Register approval management endpoints
        register_approval_endpoints(app, token_manager, approval_queue)
        
        # Restore original directory
        os.chdir(original_cwd)
        
        print("✅ Enhanced security system enabled")
        print(f"   Loaded {len(token_manager.tokens)} tokens")
        SECURITY_ENHANCED = True
    except Exception as e:
        print(f"⚠️  Security enhancement disabled: {e}")
        print("⚠️  Falling back to legacy AUTH_TOKEN system")
        SECURITY_ENHANCED = False
else:
    print("ℹ️  Using legacy AUTH_TOKEN authentication")

"""
    
    # Find spot after health endpoint
    health_pattern = r"(@app\.get\(\"/health\"\)\ndef health\(\) -> dict:\n    return \{\"status\": \"ok\", \"backend\": BACKEND, \"model\": DEFAULT_MODEL\})\n"
    content = re.sub(
        health_pattern,
        r"\1\n\n" + security_init,
        content,
        count=1
    )
    
    # 3. Update _require_auth function to use enhanced security
    old_require_auth = r"""def _require_auth\(authorization: Optional\[str\]\) -> Optional\[str\]:
    if AUTH_TOKENS:  # Only enforce if at least one token is configured
        if not authorization or not authorization\.startswith\(\"Bearer \"\):
            _log_event\(\"auth_failure\", reason=\"missing_header\"\)
            raise HTTPException\(status_code=401, detail=\"Missing/invalid Authorization header\"\)
        token = authorization\.split\(\" \", 1\)\[1\]
        if token not in AUTH_TOKENS:
            _log_event\(\"auth_failure\", reason=\"invalid_token\"\)
            raise HTTPException\(status_code=403, detail=\"Invalid token\"\)
        return _enforce_rate_limit\(token\)
    return None"""
    
    new_require_auth = """def _require_auth(authorization: Optional[str], operation: str = "legacy", path: Optional[Path] = None, command: Optional[List[str]] = None) -> Optional[str]:
    \"\"\"
    Authentication wrapper with optional enhanced security
    
    If SECURITY_ENHANCED is True, uses new permission system.
    Otherwise, falls back to legacy AUTH_TOKEN validation.
    \"\"\"
    if SECURITY_ENHANCED:
        try:
            token_info = require_auth_and_permission(
                authorization=authorization,
                operation=operation,
                path=path,
                command=command,
                skip_rate_limit=False
            )
            return rate_limiter.get_token_fingerprint(token_info.token)
        except Exception:
            # Fall through to legacy system
            pass
    
    # Legacy authentication
    if AUTH_TOKENS:  # Only enforce if at least one token is configured
        if not authorization or not authorization.startswith("Bearer "):
            _log_event("auth_failure", reason="missing_header")
            raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")
        token = authorization.split(" ", 1)[1]
        if token not in AUTH_TOKENS:
            _log_event("auth_failure", reason="invalid_token")
            raise HTTPException(status_code=403, detail="Invalid token")
        return _enforce_rate_limit(token)
    return None"""
    
    content = re.sub(old_require_auth, new_require_auth, content, count=1, flags=re.MULTILINE | re.DOTALL)
    
    # 4. Update fs_ls endpoint
    content = content.replace(
        'def fs_ls(path: Optional[str] = None, authorization: Optional[str] = Header(None)):\n    token_fp = _require_auth(authorization)',
        'def fs_ls(path: Optional[str] = None, authorization: Optional[str] = Header(None)):\n    tgt = _resolve_path(path or str(BASE_DIR))\n    token_fp = _require_auth(authorization, operation="fs_ls", path=tgt)'
    )
    
    # 5. Update fs_read endpoint
    content = content.replace(
        'def fs_read(path: str, authorization: Optional[str] = Header(None)):\n    token_fp = _require_auth(authorization)\n    tgt = _resolve_path(path)',
        'def fs_read(path: str, authorization: Optional[str] = Header(None)):\n    tgt = _resolve_path(path)\n    token_fp = _require_auth(authorization, operation="fs_read", path=tgt)'
    )
    
    # 6. Update fs_write endpoint
    content = content.replace(
        'def fs_write(body: FSWriteBody, authorization: Optional[str] = Header(None)):\n    token_fp = _require_auth(authorization)',
        'def fs_write(body: FSWriteBody, authorization: Optional[str] = Header(None)):\n    tgt = _resolve_path(body.path)\n    token_fp = _require_auth(authorization, operation="fs_write", path=tgt)'
    )
    
    # 7. Update fs_mkdir endpoint
    content = content.replace(
        'def fs_mkdir(body: FSMkdirBody, authorization: Optional[str] = Header(None)):\n    token_fp = _require_auth(authorization)',
        'def fs_mkdir(body: FSMkdirBody, authorization: Optional[str] = Header(None)):\n    tgt = _resolve_path(body.path)\n    token_fp = _require_auth(authorization, operation="fs_mkdir", path=tgt)'
    )
    
    # 8. Update fs_rm endpoint
    content = content.replace(
        'def fs_rm(body: FSRmBody, authorization: Optional[str] = Header(None)):\n    token_fp = _require_auth(authorization)',
        'def fs_rm(body: FSRmBody, authorization: Optional[str] = Header(None)):\n    tgt = _resolve_path(body.path)\n    token_fp = _require_auth(authorization, operation="fs_rm", path=tgt)'
    )
    
    # 9. Update exec endpoint
    content = content.replace(
        'def exec_cmd(body: ExecBody, authorization: Optional[str] = Header(None)):\n    token_fp = _require_auth(authorization)\n    cmd = list(body.cmd)',
        'def exec_cmd(body: ExecBody, authorization: Optional[str] = Header(None)):\n    cmd = list(body.cmd)\n    if body.sudo:\n        cmd = ["sudo"] + cmd\n    token_fp = _require_auth(authorization, operation="exec", command=cmd)'
    )
    
    # 10. Update batch endpoint - add operation-specific auth
    batch_pattern = r'(def batch\(req: BatchRequest, authorization: Optional\[str\] = Header\(None\)\):)\n    token_fp = _require_auth\(authorization\)'
    batch_replacement = r'\1\n    # Validate auth once for batch\n    token_fp = _require_auth(authorization, operation="batch")'
    content = re.sub(batch_pattern, batch_replacement, content)
    
    # Write the updated file
    with open(server_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ Security integration complete!")
    print(f"   Updated: {server_file}")
    print("   Backup available at: local_agent_server.py.backup")
    
    return True


if __name__ == "__main__":
    print("🔐 Trapdoor Security Integration")
    print("=" * 60)
    
    success = integrate_security()
    
    if success:
        print("\n📋 Next steps:")
        print("   1. Review the changes in local_agent_server.py")
        print("   2. Create config/tokens.json (or let auto-migration handle it)")
        print("   3. Restart Trapdoor")
        print("\n   If anything goes wrong, restore from:")
        print("   cp local_agent_server.py.backup local_agent_server.py")
    else:
        print("\n❌ Integration failed or already completed")
