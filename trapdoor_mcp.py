#!/usr/bin/env python3
"""
trapdoor MCP Server - Connect Claude Code instances into a mesh

This MCP server allows Claude Code to:
- Connect to the trapdoor hub as an intelligent agent
- Find and communicate with other Claude Code instances
- Delegate tasks across machines
- Coordinate complex workflows

Usage:
  Add to Claude Code's MCP config:
  {
    "trapdoor": {
      "command": "python3",
      "args": ["/path/to/trapdoor_mcp.py"]
    }
  }
"""

import asyncio
import json
import os
import socket
import sys
import requests
import base64
from pathlib import Path
from typing import Optional

# Add Trapdoor to path
TRAPDOOR_DIR = Path(__file__).parent
sys.path.insert(0, str(TRAPDOOR_DIR))

from terminal_client import TrapdoorAgent
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("trapdoor")

# Global agent instance
_agent: Optional[TrapdoorAgent] = None
_message_queue = asyncio.Queue()

# Local trapdoor server configuration
TRAPDOOR_LOCAL_URL = os.getenv("TRAPDOOR_LOCAL_URL", "http://localhost:8080")
TRAPDOOR_AUTH_TOKEN = None  # Will be loaded from file


def load_auth_token() -> Optional[str]:
    """Load auth token for local trapdoor server"""
    global TRAPDOOR_AUTH_TOKEN

    if TRAPDOOR_AUTH_TOKEN:
        return TRAPDOOR_AUTH_TOKEN

    # Try to load from environment
    token = os.getenv("AUTH_TOKEN")
    if token:
        TRAPDOOR_AUTH_TOKEN = token
        return token

    # Try to load from file
    token_file = Path.home() / "Desktop" / "auth_token.txt"
    if token_file.exists():
        try:
            TRAPDOOR_AUTH_TOKEN = token_file.read_text().strip()
            return TRAPDOOR_AUTH_TOKEN
        except Exception:
            pass

    # Try config tokens
    config_token_file = TRAPDOOR_DIR / "config" / "tokens.json"
    if config_token_file.exists():
        try:
            config = json.loads(config_token_file.read_text())
            tokens = config.get("tokens", [])
            if tokens:
                # Look for "token" field (actual token) not "token_id" (identifier)
                TRAPDOOR_AUTH_TOKEN = tokens[0].get("token")
                return TRAPDOOR_AUTH_TOKEN
        except Exception:
            pass

    return None


def trapdoor_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make authenticated request to local trapdoor server"""
    token = load_auth_token()
    headers = kwargs.pop("headers", {})

    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{TRAPDOOR_LOCAL_URL}{endpoint}"

    try:
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Trapdoor request failed: {e}")


def get_hub_url() -> str:
    """Get hub URL from environment or default"""
    return os.getenv("TRAPDOOR_HUB", "ws://100.70.207.76:8081/v1/ws/agent")


async def ensure_connected():
    """Ensure we're connected to the hub"""
    global _agent

    if _agent and _agent.running:
        return _agent

    # Create new agent
    hostname = socket.gethostname()
    agent_id = f"claude-{hostname}"

    _agent = TrapdoorAgent(get_hub_url(), agent_id=agent_id)

    # Set up message handler
    async def handle_message(from_agent, payload):
        """Queue messages for Claude to process"""
        await _message_queue.put({
            "from": from_agent,
            "payload": payload,
            "timestamp": asyncio.get_event_loop().time()
        })

    _agent.on_message(handle_message)

    # Connect with Claude Code capabilities
    await _agent.connect(
        agent_type="claude-code",
        capabilities=[
            "filesystem",
            "git",
            "processes",
            "mcp_servers",
            "ai_reasoning",
            "code_execution"
        ],
        hostname=hostname
    )

    return _agent


@mcp.tool()
async def trapdoor_connect() -> str:
    """
    Connect this Claude Code instance to the trapdoor mesh.

    Once connected, this Claude can:
    - Find other Claude instances on the network
    - Send tasks to other Claudes
    - Receive tasks from other Claudes
    - Coordinate complex workflows across machines

    Returns:
        Connection status message
    """
    try:
        agent = await ensure_connected()
        return f"✓ Connected to trapdoor mesh as {agent.agent_id}\n" \
               f"  Hub: {agent.hub_url}\n" \
               f"  You can now coordinate with other Claude instances."
    except Exception as e:
        return f"✗ Failed to connect: {e}"


@mcp.tool()
async def trapdoor_find_agents(
    capability: Optional[str] = None,
    agent_type: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    Find other Claude Code instances on the mesh.

    Args:
        capability: Filter by capability (e.g., "filesystem", "git", "ai_reasoning")
        agent_type: Filter by type (e.g., "claude-code", "browser")
        status: Filter by status (e.g., "idle", "busy")

    Returns:
        List of available Claude instances with their capabilities

    Example:
        To find idle Claude instances:
        trapdoor_find_agents(status="idle")

        To find Claudes with filesystem access:
        trapdoor_find_agents(capability="filesystem")
    """
    try:
        agent = await ensure_connected()

        criteria = {}
        if capability:
            criteria["capability"] = capability
        if agent_type:
            criteria["type"] = agent_type
        if status:
            criteria["status"] = status

        agents = await agent.find_agents(**criteria)

        if not agents:
            return "No other Claude instances found on the mesh."

        result = f"Found {len(agents)} Claude instance(s):\n\n"
        for a in agents:
            if a['id'] == agent.agent_id:
                continue  # Skip self

            result += f"• {a['id']}\n"
            result += f"  Type: {a['type']}\n"
            result += f"  Status: {a['status']}\n"
            result += f"  Hostname: {a.get('hostname', 'unknown')}\n"
            result += f"  Capabilities: {', '.join(a.get('capabilities', []))}\n\n"

        return result
    except Exception as e:
        return f"✗ Error finding agents: {e}"


@mcp.tool()
async def trapdoor_send_task(agent_id: str, task_description: str, context: Optional[str] = None) -> str:
    """
    Send a task to another Claude Code instance.

    The receiving Claude will:
    - Process the task description intelligently
    - Decide how to execute it
    - Perform the work on its local machine
    - Send results back

    Args:
        agent_id: Target Claude instance (e.g., "claude-silver-fox")
        task_description: What you need done (be specific)
        context: Optional additional context or constraints

    Returns:
        Confirmation that task was sent

    Example:
        trapdoor_send_task(
            "claude-silver-fox",
            "Check disk space and list the 10 largest directories",
            "I'm concerned about storage usage"
        )
    """
    try:
        agent = await ensure_connected()

        payload = {
            "type": "task",
            "task": task_description,
            "context": context,
            "from_claude": agent.agent_id
        }

        await agent.send_message(agent_id, payload)

        return f"✓ Task sent to {agent_id}\n" \
               f"  Task: {task_description}\n" \
               f"  The receiving Claude will process this and execute on its machine."
    except Exception as e:
        return f"✗ Failed to send task: {e}"


@mcp.tool()
async def trapdoor_check_messages() -> str:
    """
    Check for messages from other Claude Code instances.

    When other Claudes send you tasks or messages, they appear here.
    You can then decide how to respond or execute the task.

    Returns:
        Pending messages from other Claude instances
    """
    try:
        agent = await ensure_connected()

        messages = []
        while not _message_queue.empty():
            try:
                msg = _message_queue.get_nowait()
                messages.append(msg)
            except asyncio.QueueEmpty:
                break

        if not messages:
            return "No new messages from other Claude instances."

        result = f"📬 {len(messages)} message(s) from other Claude instances:\n\n"

        for msg in messages:
            result += f"From: {msg['from']}\n"

            payload = msg['payload']
            if payload.get('type') == 'task':
                result += f"Task: {payload.get('task')}\n"
                if payload.get('context'):
                    result += f"Context: {payload.get('context')}\n"
            else:
                result += f"Message: {json.dumps(payload, indent=2)}\n"

            result += "\n"

        result += "You can respond using trapdoor_send_task() or process these tasks as needed."

        return result
    except Exception as e:
        return f"✗ Error checking messages: {e}"


@mcp.tool()
async def trapdoor_broadcast(message: str) -> str:
    """
    Broadcast a message to all Claude Code instances on the mesh.

    Useful for:
    - Announcing status updates
    - Coordinating multi-machine workflows
    - Checking availability

    Args:
        message: Message to broadcast to all Claude instances

    Returns:
        Confirmation that broadcast was sent

    Example:
        trapdoor_broadcast("Starting maintenance, will be offline for 10 minutes")
    """
    try:
        agent = await ensure_connected()

        await agent.broadcast({
            "type": "broadcast",
            "message": message,
            "from_claude": agent.agent_id
        })

        return f"✓ Broadcast sent to all Claude instances: '{message}'"
    except Exception as e:
        return f"✗ Failed to broadcast: {e}"


@mcp.tool()
async def trapdoor_status() -> str:
    """
    Check your connection status to the trapdoor mesh.

    Returns:
        Current connection status and mesh information
    """
    try:
        agent = await ensure_connected()

        agents = await agent.find_agents()
        other_claudes = [a for a in agents if a['id'] != agent.agent_id]

        result = f"✓ Connected to trapdoor mesh\n\n"
        result += f"Your agent ID: {agent.agent_id}\n"
        result += f"Hub: {agent.hub_url}\n"
        result += f"Status: {agent.running and 'Connected' or 'Disconnected'}\n\n"
        result += f"Other Claude instances online: {len(other_claudes)}\n"

        if other_claudes:
            result += "\nOnline Claudes:\n"
            for a in other_claudes:
                result += f"  • {a['id']} ({a.get('hostname', 'unknown')}) - {a.get('status', 'unknown')}\n"

        return result
    except Exception as e:
        return f"✗ Error checking status: {e}"


@mcp.tool()
async def trapdoor_send_file(agent_id: str, file_path: str, remote_save_path: Optional[str] = None) -> str:
    """
    Send a file from this machine to another Claude Code instance.

    This reads the file using the local trapdoor server (with security/logging)
    and sends it through the mesh to the target Claude instance.

    Args:
        agent_id: Target Claude instance (e.g., "claude-silver-fox")
        file_path: Local file path to send
        remote_save_path: Where to save on remote machine (default: same path)

    Returns:
        Confirmation of file transfer

    Example:
        trapdoor_send_file(
            "claude-silver-fox",
            "/Users/patricksomerville/data.csv",
            "/Users/patricksomerville/shared/data.csv"
        )
    """
    try:
        agent = await ensure_connected()

        # Read file via local trapdoor server (uses security system)
        try:
            result = trapdoor_request("GET", "/fs/read", params={"path": file_path})
        except Exception as e:
            return f"✗ Failed to read file: {e}"

        # Extract content and determine encoding
        if "content" in result:
            # Text file
            content = result["content"]
            encoding = "text"
            file_size = len(content.encode('utf-8'))
        elif "bytes" in result:
            # Binary file - need to read as base64
            # Trapdoor server returns bytes count, but not the actual bytes
            # We need to get the actual file content
            file_path_obj = Path(file_path).expanduser()
            content = base64.b64encode(file_path_obj.read_bytes()).decode('ascii')
            encoding = "base64"
            file_size = result["bytes"]
        else:
            return f"✗ Unexpected response from trapdoor server"

        file_name = Path(file_path).name

        # Send file through mesh
        payload = {
            "type": "file_transfer",
            "action": "receive_file",
            "file_name": file_name,
            "content": content,
            "encoding": encoding,
            "size": file_size,
            "save_path": remote_save_path or str(file_path),
            "from_claude": agent.agent_id
        }

        await agent.send_message(agent_id, payload)

        return f"✓ File sent to {agent_id}\n" \
               f"  File: {file_path} ({file_size} bytes)\n" \
               f"  Remote path: {remote_save_path or file_path}\n" \
               f"  Encoding: {encoding}"

    except Exception as e:
        return f"✗ Failed to send file: {e}"


@mcp.tool()
async def trapdoor_request_file(agent_id: str, remote_file_path: str, local_save_path: Optional[str] = None) -> str:
    """
    Request a file from another Claude Code instance.

    This fetches a file from a remote machine and saves it locally.
    The remote Claude will read the file and send it back.

    Args:
        agent_id: Source Claude instance (e.g., "claude-silver-fox")
        remote_file_path: File path on remote machine
        local_save_path: Where to save locally (default: same filename in current dir)

    Returns:
        Confirmation of file receipt

    Example:
        trapdoor_request_file(
            "claude-silver-fox",
            "/Users/patricksomerville/logs/system.log",
            "./remote_system.log"
        )
    """
    try:
        agent = await ensure_connected()

        # Send request
        payload = {
            "type": "file_transfer",
            "action": "send_file",
            "file_path": remote_file_path,
            "requester": agent.agent_id,
            "save_path": local_save_path
        }

        await agent.send_message(agent_id, payload)

        return f"✓ File request sent to {agent_id}\n" \
               f"  Requested: {remote_file_path}\n" \
               f"  Will save to: {local_save_path or Path(remote_file_path).name}\n" \
               f"  Use trapdoor_check_messages() to see when file arrives."

    except Exception as e:
        return f"✗ Failed to request file: {e}"


@mcp.tool()
async def trapdoor_handle_file_transfers() -> str:
    """
    Process incoming file transfers from other Claude instances.

    When other Claudes send you files, this tool:
    - Receives the file data
    - Decodes it (text or binary)
    - Saves to the specified location

    Returns:
        Status of file transfers processed
    """
    try:
        agent = await ensure_connected()

        transfers_processed = 0
        messages = []

        # Check message queue for file transfers
        while not _message_queue.empty():
            try:
                msg = _message_queue.get_nowait()
                messages.append(msg)
            except asyncio.QueueEmpty:
                break

        result = ""

        for msg in messages:
            payload = msg['payload']

            # Handle file receive
            if payload.get('type') == 'file_transfer' and payload.get('action') == 'receive_file':
                from_agent = msg['from']
                content = payload.get('content')
                encoding = payload.get('encoding', 'text')
                save_path = payload.get('save_path')
                file_name = payload.get('file_name')

                # Decode content if base64
                if encoding == 'base64':
                    # Binary file - save to temp location then use trapdoor to move it
                    # For now, decode and write via trapdoor as text representation
                    # This is a limitation - trapdoor /fs/write only supports text
                    # For binary files, we'll need to save directly
                    save_path_obj = Path(save_path).expanduser()
                    save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    decoded_content = base64.b64decode(content)
                    save_path_obj.write_bytes(decoded_content)

                    result += f"✓ Received binary file from {from_agent}\n"
                    result += f"  File: {file_name} ({payload.get('size')} bytes)\n"
                    result += f"  Saved to: {save_path}\n"
                    result += f"  Note: Binary files bypass trapdoor security (limitation)\n\n"
                    transfers_processed += 1
                else:
                    # Text file - use trapdoor /fs/write endpoint (with security/logging)
                    try:
                        trapdoor_request("POST", "/fs/write", json={
                            "path": save_path,
                            "content": content,
                            "mode": "write"
                        })

                        result += f"✓ Received file from {from_agent}\n"
                        result += f"  File: {file_name} ({payload.get('size')} bytes)\n"
                        result += f"  Saved to: {save_path}\n\n"
                        transfers_processed += 1
                    except Exception as e:
                        result += f"✗ Failed to save file from {from_agent}: {e}\n\n"

            # Handle file send request
            elif payload.get('type') == 'file_transfer' and payload.get('action') == 'send_file':
                from_agent = msg['from']
                requested_path = payload.get('file_path')
                requester_save_path = payload.get('save_path')

                # Read and send file
                file_path_obj = Path(requested_path).expanduser()

                if not file_path_obj.exists():
                    await agent.send_message(from_agent, {
                        "type": "error",
                        "message": f"File not found: {requested_path}"
                    })
                    result += f"✗ File request failed: {requested_path} not found\n\n"
                    continue

                # Read file
                try:
                    content = file_path_obj.read_text()
                    encoding = "text"
                except UnicodeDecodeError:
                    import base64
                    content = base64.b64encode(file_path_obj.read_bytes()).decode('ascii')
                    encoding = "base64"

                # Send back
                await agent.send_message(from_agent, {
                    "type": "file_transfer",
                    "action": "receive_file",
                    "file_name": file_path_obj.name,
                    "content": content,
                    "encoding": encoding,
                    "size": file_path_obj.stat().st_size,
                    "save_path": requester_save_path or file_path_obj.name,
                    "from_claude": agent.agent_id
                })

                result += f"✓ Sent file to {from_agent}\n"
                result += f"  File: {requested_path} ({file_path_obj.stat().st_size} bytes)\n\n"
                transfers_processed += 1

        if transfers_processed == 0:
            return "No pending file transfers."

        return f"Processed {transfers_processed} file transfer(s):\n\n{result}"

    except Exception as e:
        return f"✗ Error handling file transfers: {e}"


@mcp.tool()
async def trapdoor_local_execute(command: list[str], cwd: Optional[str] = None, timeout: int = 300) -> str:
    """
    Execute a command on this machine using the local trapdoor server.

    This uses the trapdoor security system, so the command will be:
    - Authenticated with your token
    - Rate-limited
    - Logged/audited
    - Tracked in memory/workflow system

    Args:
        command: Command and arguments as list (e.g., ["ls", "-la", "/tmp"])
        cwd: Working directory (optional)
        timeout: Timeout in seconds (default: 300)

    Returns:
        Command output (stdout and stderr)

    Example:
        trapdoor_local_execute(["git", "status"], cwd="/Users/patricksomerville/Projects")
    """
    try:
        result = trapdoor_request("POST", "/exec", json={
            "cmd": command,
            "cwd": cwd,
            "timeout": timeout,
            "sudo": False
        })

        output = f"Command: {' '.join(command)}\n"
        output += f"Return code: {result.get('rc')}\n"
        output += f"CWD: {result.get('cwd')}\n\n"

        if result.get('stdout'):
            output += f"STDOUT:\n{result['stdout']}\n"

        if result.get('stderr'):
            output += f"STDERR:\n{result['stderr']}\n"

        return output

    except Exception as e:
        return f"✗ Failed to execute command: {e}"


@mcp.tool()
async def trapdoor_local_chat(message: str, model: Optional[str] = None) -> str:
    """
    Chat with the local Qwen 2.5 Coder 32B model via trapdoor.

    This uses the existing trapdoor server's chat endpoint, which connects
    to Ollama with Qwen. Useful for:
    - Getting code suggestions from local model
    - Analyzing code/data without sending to cloud
    - Running inference on local machine

    Args:
        message: Your message/prompt to Qwen
        model: Model to use (default: qwen2.5-coder:32b)

    Returns:
        Qwen's response

    Example:
        trapdoor_local_chat("Explain what this code does: def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)")
    """
    try:
        result = trapdoor_request("POST", "/v1/chat/completions", json={
            "model": model or "qwen2.5-coder:32b",
            "messages": [
                {"role": "user", "content": message}
            ],
            "stream": False
        })

        response = result['choices'][0]['message']['content']
        return response

    except Exception as e:
        return f"✗ Failed to chat with local model: {e}"


@mcp.tool()
async def trapdoor_coordinate_workflow(
    task_description: str,
    required_capabilities: str,
    max_agents: Optional[int] = None
) -> str:
    """
    Coordinate a complex workflow across multiple Claude instances.

    This tool helps orchestrate multi-machine tasks by:
    - Finding suitable Claude instances
    - Distributing work intelligently
    - Tracking progress

    Args:
        task_description: Overall workflow description
        required_capabilities: Comma-separated capabilities needed (e.g., "filesystem,git")
        max_agents: Maximum number of Claude instances to use (default: all available)

    Returns:
        Workflow coordination plan and status

    Example:
        trapdoor_coordinate_workflow(
            "Backup all repositories across the network",
            "filesystem,git",
            max_agents=3
        )
    """
    try:
        agent = await ensure_connected()

        # Find suitable agents
        caps = [c.strip() for c in required_capabilities.split(",")]
        all_agents = await agent.find_agents()

        # Filter agents that have ANY of the required capabilities
        suitable_agents = []
        for a in all_agents:
            if a['id'] == agent.agent_id:
                continue
            agent_caps = a.get('capabilities', [])
            if any(cap in agent_caps for cap in caps):
                suitable_agents.append(a)

        if max_agents:
            suitable_agents = suitable_agents[:max_agents]

        if not suitable_agents:
            return f"No suitable Claude instances found with capabilities: {required_capabilities}"

        result = f"📋 Workflow Coordination Plan\n\n"
        result += f"Task: {task_description}\n"
        result += f"Required capabilities: {required_capabilities}\n"
        result += f"Suitable Claude instances: {len(suitable_agents)}\n\n"

        result += "Selected Claudes:\n"
        for a in suitable_agents:
            result += f"  • {a['id']} ({a.get('hostname', 'unknown')})\n"
            result += f"    Capabilities: {', '.join(a.get('capabilities', []))}\n"

        result += f"\nUse trapdoor_send_task() to delegate specific tasks to these Claude instances."

        return result
    except Exception as e:
        return f"✗ Error coordinating workflow: {e}"


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
