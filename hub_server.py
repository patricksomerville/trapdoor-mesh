#!/usr/bin/env python3
"""
trapdoor hub - minimal WebSocket server for agent mesh
Run this on Neon (or locally for testing)
"""

import asyncio
import json
import time
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="trapdoor hub")

# Active connections: agent_id -> WebSocket
agents: Dict[str, WebSocket] = {}

# Agent metadata: agent_id -> {type, capabilities, last_seen, ...}
registry: Dict[str, dict] = {}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "agents_connected": len(agents),
        "agents": list(registry.keys())
    }


@app.get("/agents")
def list_agents():
    """List all registered agents"""
    return {
        "agents": [
            {
                "id": agent_id,
                **metadata
            }
            for agent_id, metadata in registry.items()
        ]
    }


@app.websocket("/v1/ws/agent")
async def agent_connection(websocket: WebSocket):
    await websocket.accept()
    agent_id = None

    try:
        # Wait for registration message
        data = await websocket.receive_json()

        if data.get("type") != "register":
            await websocket.send_json({"error": "First message must be registration"})
            await websocket.close()
            return

        # Register agent
        agent_id = data.get("agent_id")
        if not agent_id:
            await websocket.send_json({"error": "agent_id required"})
            await websocket.close()
            return

        agents[agent_id] = websocket
        registry[agent_id] = {
            "type": data.get("agent_type", "unknown"),
            "capabilities": data.get("capabilities", []),
            "hostname": data.get("hostname", "unknown"),
            "connected_at": time.time(),
            "last_seen": time.time(),
            "status": "idle"
        }

        print(f"✓ Agent registered: {agent_id} ({registry[agent_id]['type']})")

        # Send confirmation
        await websocket.send_json({
            "type": "registered",
            "agent_id": agent_id,
            "agents_online": len(agents)
        })

        # Broadcast to all other agents
        await broadcast({
            "type": "agent_joined",
            "agent_id": agent_id,
            "agent_type": registry[agent_id]['type']
        }, exclude=agent_id)

        # Message loop
        while True:
            message = await websocket.receive_json()
            registry[agent_id]["last_seen"] = time.time()

            await handle_message(agent_id, message)

    except WebSocketDisconnect:
        print(f"✗ Agent disconnected: {agent_id}")
    except Exception as e:
        print(f"✗ Error with agent {agent_id}: {e}")
    finally:
        # Cleanup
        if agent_id and agent_id in agents:
            del agents[agent_id]
            if agent_id in registry:
                del registry[agent_id]

            # Notify other agents
            await broadcast({
                "type": "agent_left",
                "agent_id": agent_id
            }, exclude=agent_id)


async def handle_message(from_agent: str, message: dict):
    """Route message from one agent to another or broadcast"""
    msg_type = message.get("type")

    if msg_type == "ping":
        # Simple keepalive
        await send_to_agent(from_agent, {"type": "pong"})

    elif msg_type == "find_agent":
        # Find agents matching criteria
        criteria = message.get("criteria", {})
        matches = find_agents(criteria)
        await send_to_agent(from_agent, {
            "type": "find_result",
            "request_id": message.get("request_id"),
            "agents": matches
        })

    elif msg_type == "send_message":
        # Send message to specific agent
        to_agent = message.get("to")
        payload = message.get("payload")

        if to_agent in agents:
            await send_to_agent(to_agent, {
                "type": "message",
                "from": from_agent,
                "payload": payload
            })
            # Ack to sender
            await send_to_agent(from_agent, {
                "type": "sent",
                "request_id": message.get("request_id")
            })
        else:
            await send_to_agent(from_agent, {
                "type": "error",
                "request_id": message.get("request_id"),
                "error": f"Agent {to_agent} not found"
            })

    elif msg_type == "broadcast":
        # Broadcast to all agents
        payload = message.get("payload")
        await broadcast({
            "type": "broadcast",
            "from": from_agent,
            "payload": payload
        }, exclude=from_agent)

    elif msg_type == "status_update":
        # Update agent status
        status = message.get("status")
        if from_agent in registry:
            registry[from_agent]["status"] = status
            # Broadcast status change
            await broadcast({
                "type": "agent_status",
                "agent_id": from_agent,
                "status": status
            }, exclude=from_agent)

    else:
        print(f"Unknown message type from {from_agent}: {msg_type}")


async def send_to_agent(agent_id: str, message: dict):
    """Send message to specific agent"""
    if agent_id in agents:
        try:
            await agents[agent_id].send_json(message)
        except Exception as e:
            print(f"Failed to send to {agent_id}: {e}")


async def broadcast(message: dict, exclude: str = None):
    """Broadcast message to all agents except excluded one"""
    for agent_id, ws in list(agents.items()):
        if agent_id != exclude:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"Failed to broadcast to {agent_id}: {e}")


def find_agents(criteria: dict) -> list:
    """Find agents matching criteria"""
    matches = []

    capability = criteria.get("capability")
    agent_type = criteria.get("type")
    status = criteria.get("status")

    for agent_id, metadata in registry.items():
        # Check capability
        if capability and capability not in metadata.get("capabilities", []):
            continue

        # Check type
        if agent_type and metadata.get("type") != agent_type:
            continue

        # Check status
        if status and metadata.get("status") != status:
            continue

        matches.append({
            "id": agent_id,
            **metadata
        })

    return matches


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081

    print(f"""
╔════════════════════════════════════════╗
║      trapdoor hub starting             ║
╚════════════════════════════════════════╝

WebSocket: ws://localhost:{port}/v1/ws/agent
HTTP API:  http://localhost:{port}/agents
Health:    http://localhost:{port}/health

Waiting for agents to connect...
    """)

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
