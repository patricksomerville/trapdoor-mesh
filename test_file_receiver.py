#!/usr/bin/env python3
"""Run on silver-fox to receive files from black"""

import asyncio
import sys
from pathlib import Path
import base64

sys.path.insert(0, str(Path(__file__).parent))
from terminal_client import TrapdoorAgent

async def receive_files():
    """Connect and wait for incoming file transfers"""
    print("=" * 60)
    print("FILE RECEIVER - Running on silver-fox")
    print("=" * 60)
    print()

    agent = TrapdoorAgent(
        'ws://100.70.207.76:8081/v1/ws/agent',
        'claude-silver-fox-receiver'
    )

    # Message handler for file transfers
    async def handle_message(from_agent, payload):
        print(f"\n📨 Message from {from_agent}")

        if payload.get('type') == 'file_transfer' and payload.get('action') == 'receive_file':
            print("   Type: File Transfer")
            file_name = payload.get('file_name')
            save_path = payload.get('save_path')
            content = payload.get('content')
            encoding = payload.get('encoding', 'text')
            size = payload.get('size', 0)

            print(f"   File: {file_name}")
            print(f"   Size: {size} bytes")
            print(f"   Encoding: {encoding}")
            print(f"   Save to: {save_path}")

            # Decode and save
            save_path_obj = Path(save_path)
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)

            if encoding == 'base64':
                decoded = base64.b64decode(content)
                save_path_obj.write_bytes(decoded)
            else:
                save_path_obj.write_text(content)

            print(f"   ✓ File saved to {save_path}")

            # Send confirmation back
            await agent.send_message(from_agent, {
                "type": "file_transfer_ack",
                "status": "success",
                "file": file_name,
                "saved_to": save_path
            })

        else:
            print(f"   Payload: {payload}")

    agent.on_message(handle_message)

    await agent.connect(
        agent_type='claude-code',
        capabilities=['filesystem', 'file_transfer'],
        hostname='silver-fox'
    )

    print(f"✓ Connected as {agent.agent_id}")
    print(f"✓ Listening for file transfers...")
    print()
    print("Waiting for files... (Press Ctrl+C to stop)")
    print()

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✓ Shutting down...")
        if agent.ws:
            await agent.ws.close()


if __name__ == "__main__":
    asyncio.run(receive_files())
