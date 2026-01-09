#!/usr/bin/env python3
"""Test that silver-fox can connect to mesh"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from terminal_client import TrapdoorAgent

async def test():
    print("Connecting silver-fox to mesh...")
    agent = TrapdoorAgent(
        'ws://100.70.207.76:8081/v1/ws/agent',
        'claude-silver-fox'
    )

    await agent.connect(
        agent_type='claude-code',
        capabilities=['filesystem', 'git', 'processes'],
        hostname='silver-fox'
    )

    print(f"✓ Connected as {agent.agent_id}")

    # Find other agents
    agents = await agent.find_agents()
    print(f"✓ Found {len(agents)} agent(s) on mesh:")

    for a in agents:
        agent_id = a.get('id', 'unknown')
        agent_type = a.get('type', 'unknown')
        agent_hostname = a.get('hostname', 'unknown')
        print(f"  • {agent_id} ({agent_type}) on {agent_hostname}")

    # Keep connected for a bit
    print("\nStaying connected for 5 seconds...")
    await asyncio.sleep(5)

    if agent.ws:
        await agent.ws.close()

    print("✓ Test complete")

if __name__ == "__main__":
    asyncio.run(test())
