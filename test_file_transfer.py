#!/usr/bin/env python3
"""Test file transfer between black and silver-fox via mesh"""

import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))
from terminal_client import TrapdoorAgent

async def test_black_to_silver_fox():
    """Send file from black to silver-fox"""
    print("=" * 60)
    print("TEST: File transfer black → silver-fox")
    print("=" * 60)
    print()

    # Create test file on black
    test_file = Path("/tmp/trapdoor_test_from_black.txt")
    test_content = "Hello from black! This file was sent via trapdoor mesh.\nTimestamp: 2026-01-08 03:00 PST"
    test_file.write_text(test_content)
    print(f"✓ Created test file: {test_file}")
    print(f"  Content: {len(test_content)} bytes")
    print()

    # Connect as black agent
    print("Connecting black to mesh...")
    agent_black = TrapdoorAgent(
        'ws://100.70.207.76:8081/v1/ws/agent',
        'claude-black-sender'
    )

    await agent_black.connect(
        agent_type='claude-code',
        capabilities=['filesystem', 'file_transfer'],
        hostname='black'
    )
    print(f"✓ Connected as {agent_black.agent_id}")
    print()

    # Find silver-fox
    print("Looking for silver-fox on mesh...")
    agents = await agent_black.find_agents()
    silver_fox_agents = [a for a in agents if 'silver-fox' in a.get('id', '').lower()]

    if not silver_fox_agents:
        print("✗ silver-fox not found on mesh!")
        print(f"  Available agents: {[a.get('id') for a in agents]}")
        print("  NOTE: You need to start Claude Code with MCP on silver-fox")
        await agent_black.ws.close()
        return False

    target_agent = silver_fox_agents[0]['id']
    print(f"✓ Found silver-fox: {target_agent}")
    print()

    # Send file
    print("Sending file to silver-fox...")
    payload = {
        "type": "file_transfer",
        "action": "receive_file",
        "file_name": test_file.name,
        "content": test_content,
        "encoding": "text",
        "size": len(test_content),
        "save_path": "/tmp/trapdoor_test_received_on_silver_fox.txt",
        "from_claude": agent_black.agent_id
    }

    await agent_black.send_message(target_agent, payload)
    print("✓ File transfer message sent")
    print(f"  Target: {target_agent}")
    print(f"  Remote path: /tmp/trapdoor_test_received_on_silver_fox.txt")
    print()

    # Wait a bit for transfer
    print("Waiting 3 seconds for transfer to complete...")
    await asyncio.sleep(3)

    await agent_black.ws.close()

    print()
    print("=" * 60)
    print("✓ Transfer initiated from black")
    print()
    print("Next: Check silver-fox for received file")
    print("  SSH to silver-fox and check:")
    print("  cat /tmp/trapdoor_test_received_on_silver_fox.txt")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_black_to_silver_fox())
    exit(0 if success else 1)
