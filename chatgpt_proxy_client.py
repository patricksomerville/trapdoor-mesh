"""
ChatGPT Proxy Client

Upload this file to ChatGPT to access your local Trapdoor instance via the proxy.

Prerequisites:
    1. Run chatgpt_proxy.py on your local machine
    2. Upload this file to ChatGPT
    3. Use the functions below

Usage:
    import chatgpt_proxy_client as proxy

    # Chat
    response = proxy.chat("What is 2+2?")
    print(response)

    # List files
    files = proxy.ls("/Users/patricksomerville/Desktop")
    print(files)

    # Read file
    content = proxy.read("/path/to/file.txt")
    print(content)

    # Write file
    proxy.write("/tmp/test.txt", "Hello!")

    # Execute command
    result = proxy.exec(["ls", "-la"], cwd="/tmp")
    print(result["stdout"])
"""

import requests
from typing import List, Dict, Any

# Configuration
PROXY_URL = "http://localhost:5001"

def _request(endpoint: str, method: str = "GET", **kwargs):
    """Internal request helper"""
    url = f"{PROXY_URL}{endpoint}"

    if method == "GET":
        resp = requests.get(url, **kwargs)
    elif method == "POST":
        resp = requests.post(url, **kwargs)
    else:
        raise ValueError(f"Unsupported method: {method}")

    resp.raise_for_status()
    return resp.json()


def health() -> Dict[str, Any]:
    """Check proxy and Trapdoor health"""
    return _request("/health")


def chat(prompt: str) -> str:
    """
    Chat with local model

    Args:
        prompt: Message to send

    Returns:
        Model response
    """
    result = _request("/chat", "POST", json={"prompt": prompt})
    return result.get("response", "")


def ls(path: str = "/") -> List[str]:
    """
    List directory contents

    Args:
        path: Directory path

    Returns:
        List of filenames
    """
    result = _request("/ls", params={"path": path})
    return result.get("files", [])


def read(path: str) -> str:
    """
    Read file contents

    Args:
        path: File path

    Returns:
        File contents
    """
    result = _request("/read", params={"path": path})
    return result.get("content", "")


def write(path: str, content: str) -> Dict[str, Any]:
    """
    Write file contents

    Args:
        path: File path
        content: Content to write

    Returns:
        Result dict
    """
    return _request("/write", "POST", json={"path": path, "content": content})


def exec(cmd: List[str], cwd: str = "/tmp") -> Dict[str, Any]:
    """
    Execute command

    Args:
        cmd: Command and arguments
        cwd: Working directory

    Returns:
        Dict with stdout, stderr, returncode
    """
    return _request("/exec", "POST", json={"cmd": cmd, "cwd": cwd})


def mkdir(path: str) -> Dict[str, Any]:
    """Create directory"""
    return _request("/mkdir", "POST", json={"path": path})


def rm(path: str) -> Dict[str, Any]:
    """Remove file or directory"""
    return _request("/rm", "POST", json={"path": path})


# Convenience aliases
list_files = ls
read_file = read
write_file = write
execute = exec


if __name__ == "__main__":
    print("Testing proxy connection...")
    try:
        status = health()
        print(f"✅ Proxy connected: {status}")

        print("\nTesting chat...")
        response = chat("Say hello!")
        print(f"Response: {response}")

        print("\n✅ Proxy client working!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure chatgpt_proxy.py is running on your local machine!")
