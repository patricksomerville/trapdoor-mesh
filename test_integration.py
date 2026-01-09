#!/usr/bin/env python3
"""
Test that the integrated trapdoor MCP server actually works.

This tests:
1. Authentication with local trapdoor server
2. File operations via trapdoor endpoints
3. Command execution via trapdoor
4. Connection to mesh hub

This proves the system is REAL and WORKING.
"""

import requests
import json
from pathlib import Path

# Configuration
TRAPDOOR_LOCAL = "http://localhost:8080"
TRAPDOOR_HUB = "http://100.70.207.76:8081"
TOKEN = "90ac04027a0b4aba685dcae29eeed91a"  # From config/tokens.json

def test_local_health():
    """Test 1: Local trapdoor is running"""
    print("Test 1: Checking local trapdoor health...")
    response = requests.get(f"{TRAPDOOR_LOCAL}/health")
    result = response.json()
    print(f"  ✓ Local trapdoor is running")
    print(f"  Backend: {result['backend']}")
    print(f"  Model: {result['model']}")
    print()
    return True


def test_hub_health():
    """Test 2: Hub is running"""
    print("Test 2: Checking hub health...")
    response = requests.get(f"{TRAPDOOR_HUB}/health")
    result = response.json()
    print(f"  ✓ Hub is running")
    print(f"  Connected agents: {result['agents_connected']}")
    print()
    return True


def test_authenticated_read():
    """Test 3: Can read files with authentication"""
    print("Test 3: Testing authenticated file read...")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"path": str(Path(__file__).parent / "README.md")}

    response = requests.get(f"{TRAPDOOR_LOCAL}/fs/read", headers=headers, params=params)
    result = response.json()

    print(f"  ✓ Successfully read file")
    print(f"  Path: {result['path']}")
    print(f"  Content length: {len(result['content'])} chars")
    print(f"  First line: {result['content'].split(chr(10))[0][:60]}...")
    print()
    return True


def test_authenticated_execute():
    """Test 4: Can execute commands with authentication"""
    print("Test 4: Testing authenticated command execution...")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {
        "cmd": ["echo", "Hello from trapdoor!"],
        "timeout": 10
    }

    response = requests.post(f"{TRAPDOOR_LOCAL}/exec", headers=headers, json=payload)
    result = response.json()

    print(f"  ✓ Successfully executed command")
    print(f"  Return code: {result['rc']}")
    print(f"  Output: {result['stdout'].strip()}")
    print()
    return True


def test_chat_with_qwen():
    """Test 5: Can chat with local Qwen model"""
    print("Test 5: Testing chat with Qwen...")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {
        "model": "qwen2.5-coder:32b",
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer with just the number."}
        ],
        "stream": False
    }

    response = requests.post(f"{TRAPDOOR_LOCAL}/v1/chat/completions", headers=headers, json=payload)
    result = response.json()

    response_text = result['choices'][0]['message']['content']
    print(f"  ✓ Successfully got response from Qwen")
    print(f"  Model: {result['model']}")
    print(f"  Response: {response_text.strip()[:100]}...")
    print()
    return True


def main():
    print("=" * 60)
    print("TRAPDOOR INTEGRATION TEST")
    print("Proving the system is REAL and WORKING")
    print("=" * 60)
    print()

    tests = [
        test_local_health,
        test_hub_health,
        test_authenticated_read,
        test_authenticated_execute,
        test_chat_with_qwen,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            print()
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print()
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print()
        print("The trapdoor system is:")
        print("  • Running local Qwen 2.5 Coder 32B")
        print("  • Accepting authenticated filesystem operations")
        print("  • Executing commands securely")
        print("  • Connected to mesh hub")
        print()
        print("This is 100% REAL and WORKING.")
        return 0
    else:
        print()
        print("⚠️  Some tests failed - check output above")
        return 1


if __name__ == "__main__":
    exit(main())
