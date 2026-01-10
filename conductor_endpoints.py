#!/usr/bin/env python3
"""
conductor_endpoints.py - Conductor pattern endpoints for trapdoor

These endpoints allow cloud Claude (via WebFetch) to orchestrate
local Claude Code instances and other AI resources.

Add to your trapdoor server:
    from conductor_endpoints import create_conductor_router
    app.include_router(create_conductor_router(), prefix="/conductor")
"""

import asyncio
import subprocess
import json
import os
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel


# ==============================================================================
# Configuration
# ==============================================================================

# Track spawned sessions
SESSIONS_FILE = Path.home() / ".trapdoor" / "conductor_sessions.json"


def load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        return json.loads(SESSIONS_FILE.read_text())
    return {"sessions": []}


def save_sessions(data: dict):
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps(data, indent=2))


# ==============================================================================
# Router
# ==============================================================================

def create_conductor_router():
    router = APIRouter()

    @router.get("/spawn")
    async def spawn_claude(
        prompt: str = Query(..., description="Task for Claude Code"),
        working_dir: str = Query("/Users/patricksomerville/Projects", description="Working directory"),
        background: bool = Query(True, description="Run in background"),
        timeout: int = Query(300, description="Timeout in seconds"),
        authorization: Optional[str] = Header(None)
    ):
        """
        Spawn a local Claude Code session.

        GET /conductor/spawn?prompt=Fix+the+bug&working_dir=/path/to/project

        This allows cloud Claude (via WebFetch) to spawn local Claude instances.
        """
        # Build command
        cmd = f"cd {working_dir} && claude --print --dangerously-skip-permissions"

        if background:
            # Spawn in background, capture PID
            full_cmd = f'nohup bash -c \'{cmd} --prompt "{prompt}"\' > /tmp/claude_spawn_$$.log 2>&1 & echo $!'

            try:
                result = subprocess.run(
                    ["bash", "-c", full_cmd],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                pid = result.stdout.strip()

                # Record session
                sessions = load_sessions()
                session_id = f"spawn_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pid}"
                sessions["sessions"].append({
                    "id": session_id,
                    "pid": pid,
                    "prompt": prompt[:200],
                    "working_dir": working_dir,
                    "started_at": datetime.now().isoformat(),
                    "status": "running"
                })
                save_sessions(sessions)

                return {
                    "status": "spawned",
                    "session_id": session_id,
                    "pid": pid,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "working_dir": working_dir,
                    "log_file": f"/tmp/claude_spawn_{pid}.log"
                }

            except subprocess.TimeoutExpired:
                raise HTTPException(500, "Spawn command timed out")
            except Exception as e:
                raise HTTPException(500, f"Spawn failed: {str(e)}")

        else:
            # Run synchronously (will block)
            full_cmd = f'{cmd} --prompt "{prompt}"'

            try:
                result = subprocess.run(
                    ["bash", "-c", full_cmd],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=working_dir
                )

                return {
                    "status": "completed",
                    "returncode": result.returncode,
                    "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
                    "stderr": result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
                }

            except subprocess.TimeoutExpired:
                return {"status": "timeout", "timeout": timeout}
            except Exception as e:
                raise HTTPException(500, f"Execution failed: {str(e)}")

    @router.get("/sessions")
    async def list_sessions():
        """List all spawned Claude sessions."""
        sessions = load_sessions()

        # Update status of running sessions
        for session in sessions.get("sessions", []):
            if session.get("status") == "running":
                pid = session.get("pid")
                if pid:
                    # Check if process is still running
                    try:
                        os.kill(int(pid), 0)
                    except (OSError, ValueError):
                        session["status"] = "completed"

        save_sessions(sessions)
        return sessions

    @router.get("/session/{session_id}")
    async def get_session(session_id: str):
        """Get details of a specific session."""
        sessions = load_sessions()

        for session in sessions.get("sessions", []):
            if session.get("id") == session_id:
                # Try to read log file
                pid = session.get("pid")
                log_content = None
                if pid:
                    log_file = Path(f"/tmp/claude_spawn_{pid}.log")
                    if log_file.exists():
                        try:
                            content = log_file.read_text()
                            log_content = content[-10000:] if len(content) > 10000 else content
                        except:
                            pass

                return {
                    **session,
                    "log": log_content
                }

        raise HTTPException(404, f"Session not found: {session_id}")

    @router.get("/qwen")
    async def query_qwen(
        prompt: str = Query(..., description="Prompt for Qwen"),
        system: str = Query("You are a helpful coding assistant.", description="System prompt"),
        max_tokens: int = Query(2000, description="Max tokens")
    ):
        """
        Query local Qwen model directly.

        GET /conductor/qwen?prompt=How+do+I+fix+this+error
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "qwen2.5-coder:32b",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False,
                        "options": {"num_predict": max_tokens}
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "success",
                        "model": "qwen2.5-coder:32b",
                        "response": data.get("message", {}).get("content", ""),
                        "eval_count": data.get("eval_count"),
                        "total_duration": data.get("total_duration")
                    }
                else:
                    return {
                        "status": "error",
                        "code": response.status_code,
                        "detail": response.text[:500]
                    }

        except Exception as e:
            raise HTTPException(500, f"Qwen query failed: {str(e)}")

    @router.get("/machines")
    async def list_machines():
        """List mesh machines and their status."""
        machines = {
            "black": {"ip": "100.70.207.76", "role": "orchestrator"},
            "silver-fox": {"ip": "100.121.212.93", "role": "storage"},
            "nvidia-spark": {"ip": "100.73.240.125", "role": "gpu"},
            "neon": {"ip": "100.80.193.92", "role": "docker"},
        }

        results = {}
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            for name, info in machines.items():
                try:
                    resp = await client.get(f"http://{info['ip']}:8080/health")
                    results[name] = {
                        **info,
                        "status": "online" if resp.status_code == 200 else "error",
                        "health": resp.json() if resp.status_code == 200 else None
                    }
                except:
                    results[name] = {**info, "status": "offline"}

        return results

    @router.get("/delegate")
    async def delegate_to_machine(
        machine: str = Query(..., description="Target machine"),
        endpoint: str = Query(..., description="Endpoint to call (e.g., /health, /fs/ls)"),
        path: str = Query(None, description="Path parameter if needed")
    ):
        """
        Delegate a request to another mesh machine.

        GET /conductor/delegate?machine=nvidia-spark&endpoint=/health
        """
        machines = {
            "black": "100.70.207.76",
            "silver-fox": "100.121.212.93",
            "nvidia-spark": "100.73.240.125",
            "neon": "100.80.193.92",
        }

        if machine not in machines:
            raise HTTPException(400, f"Unknown machine: {machine}")

        import httpx

        url = f"http://{machines[machine]}:8080{endpoint}"
        if path:
            url += f"?path={path}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                return {
                    "machine": machine,
                    "endpoint": endpoint,
                    "status_code": resp.status_code,
                    "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:5000]
                }
        except Exception as e:
            raise HTTPException(500, f"Delegation failed: {str(e)}")

    return router


# ==============================================================================
# Standalone server for testing
# ==============================================================================

if __name__ == "__main__":
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI(title="Conductor API", description="Orchestrate Claude Code sessions")
    app.include_router(create_conductor_router(), prefix="/conductor")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "conductor"}

    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                      CONDUCTOR API                                 ║
║           Orchestrate Claude Code across the mesh                  ║
╚═══════════════════════════════════════════════════════════════════╝

Endpoints:
  GET /conductor/spawn?prompt=...     Spawn Claude Code session
  GET /conductor/sessions             List spawned sessions
  GET /conductor/session/{id}         Get session details + log
  GET /conductor/qwen?prompt=...      Query local Qwen directly
  GET /conductor/machines             List mesh machine status
  GET /conductor/delegate?machine=... Delegate to mesh machine

Example:
  curl "http://localhost:8082/conductor/spawn?prompt=Fix+the+bug"
""")

    uvicorn.run(app, host="0.0.0.0", port=8082)
