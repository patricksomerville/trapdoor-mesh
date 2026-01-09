"""
Approval Endpoints for Trapdoor

Add these endpoints to local_agent_server.py to enable approval workflows.

Usage:
    from approval_endpoints import register_approval_endpoints
    register_approval_endpoints(app, token_manager, approval_queue)
"""

from fastapi import FastAPI, Header, HTTPException, Depends
from typing import Optional
from security import TokenManager, ApprovalQueue, TokenInfo


def register_approval_endpoints(
    app: FastAPI,
    token_manager: TokenManager,
    approval_queue: ApprovalQueue
) -> None:
    """Register approval management endpoints"""

    def require_admin_token(authorization: str = Header(...)) -> TokenInfo:
        """FastAPI dependency for admin token authentication"""
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")

        token = authorization.split(" ", 1)[1]
        token_info = token_manager.validate_token(token)

        if "admin" not in token_info.scopes:
            raise HTTPException(status_code=403, detail="Admin scope required")

        return token_info

    @app.get("/approval/pending")
    def list_pending_approvals(token_info: TokenInfo = Depends(require_admin_token)):
        """
        List all pending approval requests

        Requires: admin scope
        """
        return {
            "pending": approval_queue.list_pending()
        }
    
    @app.post("/approval/{request_id}/approve")
    def approve_operation(request_id: str, token_info: TokenInfo = Depends(require_admin_token)):
        """
        Approve a pending operation

        Requires: admin scope
        """
        if approval_queue.approve(request_id):
            return {"status": "approved", "request_id": request_id}
        else:
            raise HTTPException(status_code=404, detail="Request ID not found")
    
    @app.post("/approval/{request_id}/deny")
    def deny_operation(request_id: str, token_info: TokenInfo = Depends(require_admin_token)):
        """
        Deny a pending operation

        Requires: admin scope
        """
        if approval_queue.deny(request_id):
            return {"status": "denied", "request_id": request_id}
        else:
            raise HTTPException(status_code=404, detail="Request ID not found")
    
    @app.get("/tokens/list")
    def list_tokens(token_info: TokenInfo = Depends(require_admin_token)):
        """
        List all configured tokens (without revealing token values)

        Requires: admin scope
        """
        tokens = []
        for tid, tinfo in token_manager.tokens.items():
            tokens.append({
                "token_id": tinfo.token_id,
                "name": tinfo.name,
                "scopes": list(tinfo.scopes),
                "enabled": tinfo.enabled,
                "created": tinfo.created.isoformat(),
                "expires": tinfo.expires.isoformat() if tinfo.expires else None,
                "last_used": tinfo.last_used.isoformat() if tinfo.last_used else None,
                "metadata": tinfo.metadata
            })

        return {"tokens": tokens}
    
    @app.post("/tokens/{token_id}/rotate")
    def rotate_token(token_id: str, token_info: TokenInfo = Depends(require_admin_token)):
        """
        Rotate a token (generate new value)

        Requires: admin scope
        """
        try:
            new_token = token_manager.rotate_token(token_id)
            return {
                "token_id": token_id,
                "new_token": new_token,
                "message": "Token rotated successfully. Update clients with new token."
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @app.post("/tokens/{token_id}/disable")
    def disable_token(token_id: str, token_info: TokenInfo = Depends(require_admin_token)):
        """
        Disable a token

        Requires: admin scope
        """
        try:
            token_manager.disable_token(token_id)
            return {
                "token_id": token_id,
                "status": "disabled"
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
