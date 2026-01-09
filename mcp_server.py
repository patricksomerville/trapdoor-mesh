# /// script
# dependencies = [
#   "mcp",
#   "pydantic",
#   "requests",
#   "fastapi",
#   "uvicorn"
# ]
# ///

import sys
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Sequence

# Add current directory to path to allow imports from sibling modules
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
import mcp.types as types

# Try to import security module
try:
    from security import TokenManager, TokenInfo, PermissionError
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    print("Warning: security.py not found. Running without security checks.")

# Try to import memory module
try:
    from memory import store as memory_store
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# Initialize MCP Server
mcp = FastMCP("Trapdoor")

# ============================================================
# CONFIGURATION & SECURITY
# ============================================================

BASE_DIR = Path(os.getenv("BASE_DIR", os.getcwd())).resolve()
ALLOW_ABSOLUTE = os.getenv("ALLOW_ABSOLUTE", "1") == "1"
# Default to ALLOW_SUDO=1 per user permission
ALLOW_SUDO = os.getenv("ALLOW_SUDO", "1") == "1" 
TRAPDOOR_ROOT = Path(__file__).parent

# Initialize Security
token_manager = None
admin_token_info = None

if SECURITY_AVAILABLE:
    try:
        config_path = TRAPDOOR_ROOT / "config" / "tokens.json"
        token_manager = TokenManager(config_path)
        
        # Create a synthetic token for MCP (Local usage = Admin-ish but restricted by global rules)
        # We include "exec:sudo" by default based on user permission
        admin_token_info = TokenInfo(
            token_id="mcp_local",
            name="MCP Local User",
            token="local",
            scopes={"read", "write", "exec", "exec:sudo"},
            created=None,
            enabled=True
        )
    except Exception as e:
        print(f"Failed to initialize security: {e}")
        SECURITY_AVAILABLE = False

# ============================================================
# HELPERS
# ============================================================

def _check_perm(operation: str, path: Optional[Path] = None, command: Optional[List[str]] = None):
    """Check permissions using security.py logic if available"""
    if not SECURITY_AVAILABLE or not token_manager:
        return

    try:
        token_manager.check_permission(
            token_info=admin_token_info,
            operation=operation,
            path=path,
            command=command
        )
    except PermissionError as e:
        raise RuntimeError(f"Permission denied: {str(e)}")

def _resolve_path(p: str) -> Path:
    path = Path(p).expanduser()
    if not ALLOW_ABSOLUTE and not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    else:
        path = path.resolve()
    
    if not ALLOW_ABSOLUTE and BASE_DIR not in path.parents and path != BASE_DIR:
        raise RuntimeError(f"Path outside BASE_DIR not allowed: {path}")
    
    return path

def _log_memory(kind: str, data: Dict[str, Any]):
    """Record event to Trapdoor memory if available"""
    if MEMORY_AVAILABLE and memory_store:
        try:
            memory_store.record_event(kind, data)
        except Exception:
            pass

# ============================================================
# MCP TOOLS
# ============================================================

@mcp.tool()
def ls(path: str = ".") -> str:
    """
    List contents of a directory.
    
    Args:
        path: Directory path to list (default: current dir)
    """
    try:
        target = _resolve_path(path)
        _check_perm("fs_ls", path=target)
        
        if not target.exists():
            return f"Error: Path not found: {target}"
            
        if target.is_file():
            stat = target.stat()
            return f"File: {target.name}\nSize: {stat.st_size} bytes"
            
        entries = []
        for entry in sorted(target.iterdir()):
            prefix = "[DIR] " if entry.is_dir() else "[FILE]"
            entries.append(f"{prefix} {entry.name}")
            
        result = "\n".join(entries)
        _log_memory("fs_ls", {"path": str(target), "entries": len(entries)})
        return result
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def read(path: str) -> str:
    """
    Read file contents.
    
    Args:
        path: Path to the file to read
    """
    try:
        target = _resolve_path(path)
        _check_perm("fs_read", path=target)
        
        if not target.exists():
            return f"Error: File not found: {target}"
        if not target.is_file():
            return f"Error: Not a file: {target}"
            
        try:
            content = target.read_text(encoding="utf-8")
            _log_memory("fs_read", {"path": str(target), "bytes": len(content)})
            return content
        except UnicodeDecodeError:
            return f"Error: Binary file detected (cannot display text): {target.name}"
            
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def write(path: str, content: str) -> str:
    """
    Write content to a file (overwrites).
    
    Args:
        path: Path to the file
        content: Content to write
    """
    try:
        target = _resolve_path(path)
        _check_perm("fs_write", path=target)
        
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        
        _log_memory("fs_write", {"path": str(target), "bytes": len(content)})
        return f"Successfully wrote {len(content)} characters to {target}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def mkdir(path: str) -> str:
    """
    Create a directory (recursive).
    
    Args:
        path: Directory path to create
    """
    try:
        target = _resolve_path(path)
        _check_perm("fs_mkdir", path=target)
        
        target.mkdir(parents=True, exist_ok=True)
        _log_memory("fs_mkdir", {"path": str(target)})
        return f"Created directory: {target}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def rm(path: str, recursive: bool = False) -> str:
    """
    Remove a file or directory.
    
    Args:
        path: Path to remove
        recursive: Set to True to delete directories recursively
    """
    try:
        target = _resolve_path(path)
        # Special permission check for destructive action
        _check_perm("fs_rm", path=target)

        if not target.exists():
            return f"Error: Path not found: {target}"
            
        if target.is_dir():
            if recursive:
                shutil.rmtree(target)
                msg = f"Recursively removed directory: {target}"
            else:
                target.rmdir()
                msg = f"Removed empty directory: {target}"
        else:
            target.unlink()
            msg = f"Removed file: {target}"
            
        _log_memory("fs_rm", {"path": str(target), "recursive": recursive})
        return msg
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def execute(command: str, cwd: str = ".") -> str:
    """
    Execute a shell command.
    
    Args:
        command: The shell command string to execute
        cwd: Working directory (default: current dir)
    """
    try:
        working_dir = _resolve_path(cwd)
        cmd_list = command.split() # Simple split
        
        _check_perm("exec", command=cmd_list)
        
        if "sudo" in cmd_list and not ALLOW_SUDO:
             return "Error: sudo not allowed by configuration"

        result = subprocess.run(
            command,
            shell=True, 
            cwd=str(working_dir),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )
        
        output = f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        output += f"\nReturn Code: {result.returncode}"
        
        _log_memory("exec", {"cmd": command, "cwd": str(working_dir), "rc": result.returncode})
        return output
        
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out (300s)"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="stdio")
