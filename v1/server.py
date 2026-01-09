#!/usr/bin/env python3
"""
Trapdoor 1.0 - Give cloud AIs safe access to your local machine

A minimal, secure bridge that exposes your filesystem and shell to
cloud-based AI agents (ChatGPT, Claude, etc.) via a simple HTTP API.

Run:
    python server.py

Then expose via ngrok/cloudflare:
    ngrok http 8080

Usage from cloud AI:
    Upload connector.py and use td.ls(), td.read(), td.exec_command(), etc.
"""

import os
import secrets
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ==============================================================================
# Configuration
# ==============================================================================

PORT = int(os.getenv("TRAPDOOR_PORT", "8080"))
TOKEN_FILE = Path(os.getenv("TRAPDOOR_TOKEN_FILE", Path.home() / ".trapdoor" / "token"))
ALLOW_EXEC = os.getenv("TRAPDOOR_ALLOW_EXEC", "1") == "1"

# ==============================================================================
# Token Management
# ==============================================================================

def get_or_create_token() -> str:
    """Get existing token or create a new one"""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()

    # Generate new token
    token = secrets.token_hex(16)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)
    print(f"\n🔑 New token generated and saved to {TOKEN_FILE}")
    return token

TOKEN = get_or_create_token()

# ==============================================================================
# FastAPI App
# ==============================================================================

app = FastAPI(
    title="Trapdoor 1.0",
    description="Give cloud AIs safe access to your local machine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Authentication
# ==============================================================================

def require_auth(authorization: Optional[str] = Header(None)) -> str:
    """Validate Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.split(" ", 1)[1]
    if token != TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    return token

# ==============================================================================
# Request/Response Models
# ==============================================================================

class WriteRequest(BaseModel):
    path: str
    content: str
    mode: str = "write"  # write or append

class MkdirRequest(BaseModel):
    path: str

class RmRequest(BaseModel):
    path: str

class ExecRequest(BaseModel):
    cmd: List[str]
    cwd: str = "/tmp"
    timeout: int = 60

class ChatRequest(BaseModel):
    model: str = "gpt-4"
    messages: list

# ==============================================================================
# Health Endpoint (No Auth)
# ==============================================================================

@app.get("/health")
def health():
    """Health check - no auth required"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "exec_enabled": ALLOW_EXEC,
        "timestamp": datetime.now().isoformat()
    }

# ==============================================================================
# Filesystem Endpoints
# ==============================================================================

@app.get("/fs/ls")
def fs_ls(
    path: str = Query("/"),
    authorization: Optional[str] = Header(None)
):
    """List directory contents"""
    require_auth(authorization)

    target = Path(path).expanduser().resolve()

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    if not target.is_dir():
        # Return file info
        stat = target.stat()
        return {
            "path": str(target),
            "type": "file",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    entries = []
    for item in sorted(target.iterdir()):
        try:
            stat = item.stat()
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else None,
            })
        except PermissionError:
            entries.append({"name": item.name, "type": "unknown", "error": "permission denied"})

    return {"path": str(target), "entries": entries}


@app.get("/fs/read")
def fs_read(
    path: str,
    authorization: Optional[str] = Header(None)
):
    """Read file contents"""
    require_auth(authorization)

    target = Path(path).expanduser().resolve()

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    try:
        content = target.read_text()
        return {"path": str(target), "content": content, "size": len(content)}
    except UnicodeDecodeError:
        return {"path": str(target), "error": "binary file", "size": target.stat().st_size}


@app.post("/fs/write")
def fs_write(
    req: WriteRequest,
    authorization: Optional[str] = Header(None)
):
    """Write content to file"""
    require_auth(authorization)

    target = Path(req.path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    if req.mode == "append":
        with open(target, "a") as f:
            f.write(req.content)
    else:
        target.write_text(req.content)

    return {"path": str(target), "written": len(req.content), "mode": req.mode}


@app.post("/fs/mkdir")
def fs_mkdir(
    req: MkdirRequest,
    authorization: Optional[str] = Header(None)
):
    """Create directory"""
    require_auth(authorization)

    target = Path(req.path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    return {"path": str(target), "created": True}


@app.post("/fs/rm")
def fs_rm(
    req: RmRequest,
    authorization: Optional[str] = Header(None)
):
    """Remove file or directory"""
    require_auth(authorization)

    target = Path(req.path).expanduser().resolve()

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {req.path}")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return {"path": str(target), "removed": True}

# ==============================================================================
# Command Execution
# ==============================================================================

@app.post("/exec")
def exec_command(
    req: ExecRequest,
    authorization: Optional[str] = Header(None)
):
    """Execute shell command"""
    require_auth(authorization)

    if not ALLOW_EXEC:
        raise HTTPException(status_code=403, detail="Command execution disabled")

    try:
        result = subprocess.run(
            req.cmd,
            cwd=req.cwd,
            capture_output=True,
            text=True,
            timeout=req.timeout
        )

        return {
            "cmd": req.cmd,
            "cwd": req.cwd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Command timed out after {req.timeout}s")
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Command not found: {req.cmd[0]}")

# ==============================================================================
# Chat Proxy (Optional - forwards to local LLM)
# ==============================================================================

@app.post("/v1/chat/completions")
def chat_completions(
    req: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    OpenAI-compatible chat endpoint.

    By default returns a placeholder. Configure OLLAMA_HOST to proxy to Ollama,
    or override this endpoint to proxy to your preferred LLM.
    """
    require_auth(authorization)

    ollama_host = os.getenv("OLLAMA_HOST")

    if ollama_host:
        # Proxy to Ollama
        import requests
        resp = requests.post(
            f"{ollama_host}/v1/chat/completions",
            json={"model": req.model, "messages": req.messages}
        )
        return resp.json()

    # Default: return placeholder
    return {
        "id": "trapdoor-1",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Chat proxy not configured. Set OLLAMA_HOST to enable."
            },
            "finish_reason": "stop"
        }]
    }

# ==============================================================================
# Main
# ==============================================================================

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                      TRAPDOOR 1.0                                 ║
║         Give cloud AIs safe access to your local machine          ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    print(f"🌐 Server:  http://localhost:{PORT}")
    print(f"🔑 Token:   {TOKEN}")
    print(f"📁 Config:  {TOKEN_FILE}")
    print(f"⚡ Exec:    {'enabled' if ALLOW_EXEC else 'disabled'}")
    print()
    print("To expose publicly, run:")
    print(f"    ngrok http {PORT}")
    print()
    print("Then upload connector.py to ChatGPT/Claude with your ngrok URL + token")
    print("─" * 67)

    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
