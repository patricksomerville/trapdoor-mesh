#!/usr/bin/env python3
"""
trapdoor terminal client - connect Claude Code instances to the hub

Usage:
    from terminal_client import TrapdoorAgent

    agent = TrapdoorAgent("ws://localhost:8081/v1/ws/agent")
    await agent.connect()

    # Find other agents
    others = await agent.find_agents(capability="filesystem")

    # Send message
    await agent.send_message(other_agent_id, {"task": "..."})
"""

import asyncio
import json
import socket
import uuid
from typing import Optional, List, Dict, Callable
import websockets


class TrapdoorAgent:
    def __init__(self, hub_url: str, agent_id: Optional[str] = None):
        self.hub_url = hub_url
        self.agent_id = agent_id or f"terminal-{uuid.uuid4().hex[:8]}"
        self.ws = None
        self.running = False
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}

    async def connect(
        self,
        agent_type: str = "terminal",
        capabilities: List[str] = None,
        hostname: Optional[str] = None
    ):
        """Connect to hub and register"""
        if capabilities is None:
            capabilities = ["filesystem", "git", "processes"]

        if hostname is None:
            hostname = socket.gethostname()

        print(f"→ Connecting to hub as {self.agent_id}...")

        self.ws = await websockets.connect(self.hub_url)

        # Register
        await self.ws.send(json.dumps({
            "type": "register",
            "agent_id": self.agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "hostname": hostname
        }))

        # Wait for confirmation
        response = json.loads(await self.ws.recv())

        if response.get("type") == "registered":
            print(f"✓ Connected as {self.agent_id}")
            print(f"  {response.get('agents_online', 0)} agents online")
            self.running = True

            # Start message loop
            asyncio.create_task(self._message_loop())
        else:
            print(f"✗ Registration failed: {response}")
            raise Exception("Registration failed")

    async def disconnect(self):
        """Disconnect from hub"""
        self.running = False
        if self.ws:
            await self.ws.close()
            print(f"✓ Disconnected")

    async def _message_loop(self):
        """Receive and handle messages from hub"""
        try:
            while self.running:
                message = json.loads(await self.ws.recv())
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("✗ Connection closed")
            self.running = False
        except Exception as e:
            print(f"✗ Error in message loop: {e}")
            self.running = False

    async def _handle_message(self, message: dict):
        """Route incoming messages"""
        msg_type = message.get("type")

        # Handle request responses
        request_id = message.get("request_id")
        if request_id and request_id in self.pending_requests:
            self.pending_requests[request_id].set_result(message)
            return

        # Handle broadcasts
        if msg_type == "agent_joined":
            print(f"→ Agent joined: {message.get('agent_id')} ({message.get('agent_type')})")

        elif msg_type == "agent_left":
            print(f"← Agent left: {message.get('agent_id')}")

        elif msg_type == "agent_status":
            print(f"● Agent status: {message.get('agent_id')} → {message.get('status')}")

        elif msg_type == "message":
            # Message from another agent
            from_agent = message.get("from")
            payload = message.get("payload")
            print(f"\n📨 Message from {from_agent}:")
            print(f"   {json.dumps(payload, indent=2)}\n")

            # Call handler if registered
            if "message" in self.message_handlers:
                await self.message_handlers["message"](from_agent, payload)

        elif msg_type == "broadcast":
            from_agent = message.get("from")
            payload = message.get("payload")
            print(f"\n📢 Broadcast from {from_agent}:")
            print(f"   {json.dumps(payload, indent=2)}\n")

    async def find_agents(self, **criteria) -> List[dict]:
        """Find agents matching criteria"""
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.ws.send(json.dumps({
            "type": "find_agent",
            "request_id": request_id,
            "criteria": criteria
        }))

        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=5.0)
            return response.get("agents", [])
        except asyncio.TimeoutError:
            print("✗ Find agents timeout")
            return []
        finally:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]

    async def send_message(self, to_agent: str, payload: dict):
        """Send message to specific agent"""
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.ws.send(json.dumps({
            "type": "send_message",
            "request_id": request_id,
            "to": to_agent,
            "payload": payload
        }))

        # Wait for confirmation
        try:
            response = await asyncio.wait_for(future, timeout=5.0)
            if response.get("type") == "sent":
                print(f"✓ Message sent to {to_agent}")
            else:
                print(f"✗ Failed to send: {response.get('error')}")
        except asyncio.TimeoutError:
            print("✗ Send message timeout")
        finally:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]

    async def broadcast(self, payload: dict):
        """Broadcast message to all agents"""
        await self.ws.send(json.dumps({
            "type": "broadcast",
            "payload": payload
        }))
        print(f"✓ Broadcast sent")

    async def update_status(self, status: str):
        """Update agent status (idle, busy, offline)"""
        await self.ws.send(json.dumps({
            "type": "status_update",
            "status": status
        }))

    def on_message(self, handler: Callable):
        """Register message handler"""
        self.message_handlers["message"] = handler

    async def ping(self):
        """Send keepalive ping"""
        await self.ws.send(json.dumps({"type": "ping"}))


# Convenience function for quick testing
async def test_connection(hub_url: str = "ws://localhost:8081/v1/ws/agent"):
    """Quick connection test"""
    agent = TrapdoorAgent(hub_url)
    await agent.connect()

    print("\n→ Finding other agents...")
    others = await agent.find_agents()
    print(f"✓ Found {len(others)} other agents:")
    for other in others:
        print(f"  - {other['id']} ({other['type']}) - {other['status']}")

    print("\n→ Testing broadcast...")
    await agent.broadcast({"message": "Hello from test agent!"})

    print("\n→ Waiting 5 seconds for messages...")
    await asyncio.sleep(5)

    await agent.disconnect()


if __name__ == "__main__":
    print("trapdoor terminal client\n")
    asyncio.run(test_connection())
