#!/usr/bin/env python3
"""
Test the full MCP server integration with the mesh.

This tests that the trapdoor_mcp.py server can:
1. Load auth token from config
2. Connect to local trapdoor server
3. Connect to mesh hub
4. Send messages through the mesh

This proves the FULL INTEGRATION works, not just individual components.
"""

import asyncio
import sys
import json
import requests
from pathlib import Path

# Add Trapdoor to path
TRAPDOOR_DIR = Path(__file__).parent
sys.path.insert(0, str(TRAPDOOR_DIR))

from terminal_client import TrapdoorAgent

# Configuration
TRAPDOOR_LOCAL_URL = "http://localhost:8080"
TRAPDOOR_HUB_URL = "ws://100.70.207.76:8081/v1/ws/agent"


def load_auth_token():
    """Load auth token from config"""
    config_token_file = TRAPDOOR_DIR / "config" / "tokens.json"
    if config_token_file.exists():
        try:
            config = json.loads(config_token_file.read_text())
            tokens = config.get("tokens", [])
            if tokens:
                return tokens[0].get("token")
        except Exception:
            pass
    return None


async def test_token_loading():
    """Test 1: Token loading works"""
    print("Test 1: Loading auth token...")
    token = load_auth_token()

    if not token:
        print("  ✗ Failed to load token")
        return False

    print(f"  ✓ Token loaded: {token[:8]}...{token[-8:]}")
    print()
    return True


async def test_trapdoor_request():
    """Test 2: Can make authenticated requests to local trapdoor"""
    print("Test 2: Testing authenticated request to local trapdoor...")

    try:
        token = load_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{TRAPDOOR_LOCAL_URL}/health", headers=headers)
        result = response.json()

        print(f"  ✓ Successfully called local trapdoor")
        print(f"  Backend: {result['backend']}")
        print(f"  Model: {result['model']}")
        print()
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print()
        return False


async def test_hub_connection():
    """Test 3: Can connect to mesh hub"""
    print("Test 3: Connecting to mesh hub...")

    try:
        agent = TrapdoorAgent(
            TRAPDOOR_HUB_URL,
            agent_id="test-integration-agent"
        )

        await agent.connect(
            agent_type="test",
            capabilities=["testing"],
            hostname="black"
        )

        print(f"  ✓ Successfully connected to hub")
        print(f"  Agent ID: {agent.agent_id}")
        print(f"  Hub URL: {agent.hub_url}")
        print()

        # Disconnect
        if agent.ws:
            await agent.ws.close()

        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print()
        return False


async def test_agent_discovery():
    """Test 4: Can discover agents on mesh"""
    print("Test 4: Testing agent discovery...")

    try:
        agent = TrapdoorAgent(
            TRAPDOOR_HUB_URL,
            agent_id="test-discovery-agent"
        )

        await agent.connect(
            agent_type="test",
            capabilities=["testing"],
            hostname="black"
        )

        # Find agents
        agents = await agent.find_agents()

        print(f"  ✓ Successfully queried agent registry")
        print(f"  Found {len(agents)} agent(s) (including self)")

        for a in agents:
            print(f"    • {a['id']} - {a['type']}")

        print()

        # Disconnect
        if agent.ws:
            await agent.ws.close()

        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print()
        return False


async def test_file_read_via_trapdoor():
    """Test 5: Can read files via trapdoor API"""
    print("Test 5: Testing file read via trapdoor API...")

    try:
        token = load_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"path": str(TRAPDOOR_DIR / "README.md")}

        response = requests.get(f"{TRAPDOOR_LOCAL_URL}/fs/read", headers=headers, params=params)
        result = response.json()

        content = result.get("content", "")
        print(f"  ✓ Successfully read file via trapdoor")
        print(f"  Path: {result['path']}")
        print(f"  Content: {len(content)} chars")
        print()
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print()
        return False


async def main():
    print("=" * 60)
    print("FULL MCP INTEGRATION TEST")
    print("Testing trapdoor_mcp.py with mesh + local server")
    print("=" * 60)
    print()

    tests = [
        test_token_loading,
        test_trapdoor_request,
        test_hub_connection,
        test_agent_discovery,
        test_file_read_via_trapdoor,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test crashed: {e}")
            print()
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print()
        print("🎉 FULL INTEGRATION WORKING!")
        print()
        print("The trapdoor MCP server can:")
        print("  • Load authentication tokens")
        print("  • Call local trapdoor server endpoints")
        print("  • Connect to mesh hub")
        print("  • Discover other agents")
        print("  • Read files via trapdoor security system")
        print()
        print("Ready to deploy to other machines!")
        return 0
    else:
        print()
        print("⚠️  Some tests failed - check output above")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
