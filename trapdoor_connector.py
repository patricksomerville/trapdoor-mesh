"""
Trapdoor Connector - Proxy script for sandboxed AI agents

Upload this file to ChatGPT/Claude/etc. to let them access your local Trapdoor instance.

Usage in sandboxed environment:
    import trapdoor_connector as td

    # List files
    files = td.ls("/Users/patricksomerville/Desktop")

    # Chat with local model
    response = td.chat("What is 2+2?")

    # Read file
    content = td.read_file("/path/to/file.txt")

    # Write file
    td.write_file("/path/to/output.txt", "Hello!")

    # Execute command
    result = td.exec_command(["ls", "-la"], cwd="/tmp")
"""

import requests
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


def _get_token() -> str:
    """
    Get Trapdoor authentication token from environment or config file.

    Tries in order:
    1. TRAPDOOR_TOKEN environment variable
    2. ~/.trapdoor/token config file

    Returns:
        Authentication token

    Raises:
        ValueError: If no token found
    """
    # Try environment variable first
    token = os.environ.get("TRAPDOOR_TOKEN")
    if token:
        return token.strip()

    # Fall back to config file
    token_file = Path.home() / ".trapdoor" / "token"
    if token_file.exists():
        return token_file.read_text().strip()

    # No token found
    raise ValueError(
        "No Trapdoor token found. Either:\n"
        "  1. Set TRAPDOOR_TOKEN environment variable:\n"
        "     export TRAPDOOR_TOKEN='your-token-here'\n"
        f"  2. Create {token_file} with your token:\n"
        f"     mkdir -p {token_file.parent} && echo 'your-token' > {token_file}\n"
        "\n"
        "Get your token from Trapdoor control panel or config/tokens.json"
    )


# Configuration
BASE_URL = "https://trapdoor.treehouse.tech"
TOKEN = _get_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# ==================== Chat ====================

def chat(prompt: str, model: str = "qwen2.5-coder:32b") -> str:
    """
    Send a message to the local model via Trapdoor

    Args:
        prompt: Message to send
        model: Model name (default: qwen2.5-coder:32b)

    Returns:
        Response from the model
    """
    r = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def chat_raw(messages: List[Dict[str, str]], model: str = "qwen2.5-coder:32b") -> Dict[str, Any]:
    """
    Send raw OpenAI-format messages to the local model

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name

    Returns:
        Full OpenAI-compatible response
    """
    r = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=HEADERS,
        json={"model": model, "messages": messages}
    )
    r.raise_for_status()
    return r.json()


# ==================== Filesystem ====================

def ls(path: str = "/") -> List[str]:
    """
    List directory contents

    Args:
        path: Directory path to list

    Returns:
        List of file/directory names
    """
    r = requests.get(
        f"{BASE_URL}/fs/ls",
        headers=HEADERS,
        params={"path": path}
    )
    r.raise_for_status()
    result = r.json()
    # API returns {"path": "...", "entries": [...]}
    if isinstance(result, dict) and "entries" in result:
        return [e["name"] for e in result["entries"]]
    return result


def read_file(path: str) -> str:
    """
    Read file contents

    Args:
        path: Path to file

    Returns:
        File contents as string
    """
    r = requests.get(
        f"{BASE_URL}/fs/read",
        headers=HEADERS,
        params={"path": path}
    )
    r.raise_for_status()
    data = r.json()
    return data.get("content", data)


def write_file(path: str, content: str) -> Dict[str, Any]:
    """
    Write content to file

    Args:
        path: Path to file
        content: Content to write

    Returns:
        Response from server
    """
    r = requests.post(
        f"{BASE_URL}/fs/write",
        headers=HEADERS,
        json={"path": path, "content": content}
    )
    r.raise_for_status()
    return r.json()


def mkdir(path: str) -> Dict[str, Any]:
    """
    Create directory

    Args:
        path: Directory path to create

    Returns:
        Response from server
    """
    r = requests.post(
        f"{BASE_URL}/fs/mkdir",
        headers=HEADERS,
        json={"path": path}
    )
    r.raise_for_status()
    return r.json()


def rm(path: str) -> Dict[str, Any]:
    """
    Remove file or directory

    Args:
        path: Path to remove

    Returns:
        Response from server
    """
    r = requests.post(
        f"{BASE_URL}/fs/rm",
        headers=HEADERS,
        json={"path": path}
    )
    r.raise_for_status()
    return r.json()


# ==================== Command Execution ====================

def exec_command(command: List[str], cwd: str = "/tmp") -> Dict[str, Any]:
    """
    Execute a command on the remote system

    Args:
        command: Command and arguments as list (e.g., ["ls", "-la"])
        cwd: Working directory for command

    Returns:
        Dict with 'stdout', 'stderr', 'returncode'
    """
    r = requests.post(
        f"{BASE_URL}/exec",
        headers=HEADERS,
        json={"path": cwd, "cmd": command}  # API uses 'cmd' not 'command'
    )
    r.raise_for_status()
    return r.json()


def run(cmd_string: str, cwd: str = "/tmp") -> str:
    """
    Execute a shell command (convenience wrapper)

    Args:
        cmd_string: Command as string (will be split on spaces)
        cwd: Working directory

    Returns:
        Command stdout
    """
    result = exec_command(cmd_string.split(), cwd=cwd)
    return result.get("stdout", "")


# ==================== Health Check ====================

def health() -> Dict[str, Any]:
    """Check if Trapdoor is reachable"""
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    r.raise_for_status()
    return r.json()


def test_connection() -> bool:
    """Test if connection to Trapdoor is working"""
    try:
        status = health()
        print(f"✅ Connected to Trapdoor")
        print(f"   Backend: {status.get('backend')}")
        print(f"   Model: {status.get('model')}")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to Trapdoor: {e}")
        return False


# ==================== Convenience Aliases ====================

# Short aliases
read = read_file
write = write_file
execute = exec_command

# Alternative names
list_dir = ls
make_dir = mkdir
remove = rm


# ==================== Example Usage ====================

if __name__ == "__main__":
    print("Trapdoor Connector - Testing connection...\n")

    if test_connection():
        print("\n--- Example: List Desktop ---")
        files = ls("/Users/patricksomerville/Desktop")
        print(f"Found {len(files)} items")
        items = list(files) if isinstance(files, dict) else files
        for f in items[:5]:
            print(f"  - {f}")

        print("\n--- Example: Chat ---")
        response = chat("What is the capital of France?")
        print(f"Response: {response}")

        print("\n--- Example: Execute Command ---")
        result = run("echo Hello from Trapdoor!")
        print(f"Output: {result}")

        print("\n✅ All examples completed successfully")
    else:
        print("\n❌ Connection test failed")
