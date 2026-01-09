#!/usr/bin/env python3
"""Test two agents communicating"""

import asyncio
from terminal_client import TrapdoorAgent


async def agent_a():
    """First agent - sends message"""
    agent = TrapdoorAgent("ws://localhost:8081/v1/ws/agent", agent_id="agent-a")
    await agent.connect(agent_type="test-sender")

    print("\n[Agent A] Waiting 2 seconds for other agent...")
    await asyncio.sleep(2)

    # Find other agents
    others = await agent.find_agents()
    print(f"[Agent A] Found {len(others)} agents")

    # Send message to agent-b
    target = next((a for a in others if a['id'] == 'agent-b'), None)
    if target:
        print(f"[Agent A] Sending message to {target['id']}...")
        await agent.send_message("agent-b", {
            "task": "List files in ~/Projects/Trapdoor",
            "priority": "high"
        })

    # Wait for response
    await asyncio.sleep(5)
    await agent.disconnect()


async def agent_b():
    """Second agent - receives and responds"""
    agent = TrapdoorAgent("ws://localhost:8081/v1/ws/agent", agent_id="agent-b")

    # Set up message handler
    async def handle_message(from_agent, payload):
        print(f"\n[Agent B] Received task from {from_agent}")
        print(f"[Agent B] Task: {payload.get('task')}")
        print(f"[Agent B] Priority: {payload.get('priority')}")

        # Simulate doing work
        await asyncio.sleep(1)
        await agent.update_status("busy")

        await asyncio.sleep(2)

        # Send response back
        await agent.send_message(from_agent, {
            "status": "complete",
            "result": ["README.md", "hub_server.py", "terminal_client.py", "..."],
            "duration_ms": 150
        })

        await agent.update_status("idle")

    agent.on_message(handle_message)

    await agent.connect(agent_type="test-receiver", capabilities=["filesystem"])

    print("[Agent B] Waiting for messages...")

    # Keep alive
    await asyncio.sleep(10)
    await agent.disconnect()


async def main():
    """Run both agents simultaneously"""
    print("╔════════════════════════════════════════╗")
    print("║  Testing two agents communicating     ║")
    print("╚════════════════════════════════════════╝\n")

    # Run both agents concurrently
    await asyncio.gather(
        agent_b(),  # Start receiver first
        agent_a()   # Then sender
    )

    print("\n✓ Test complete")


if __name__ == "__main__":
    asyncio.run(main())
