#!/usr/bin/env python3
"""
spawn_claude.py - Spawn Claude Code sessions across the mesh

Usage:
    python spawn_claude.py black "Fix the bug in server.py"
    python spawn_claude.py nvidia-spark "Run heavy computation" --background
    python spawn_claude.py --list  # Show available machines

This script uses the mesh connector to spawn Claude Code instances
on remote machines, allowing the Conductor (cloud Claude) to delegate
complex tasks to local Claude instances with full filesystem access.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Import mesh connector if available
try:
    from mesh_connector import MeshConnector, MACHINES
    MESH_AVAILABLE = True
except ImportError:
    MESH_AVAILABLE = False
    MACHINES = {
        "black": {"tailscale_ip": "100.70.207.76"},
        "silver-fox": {"tailscale_ip": "100.121.212.93"},
        "nvidia-spark": {"tailscale_ip": "100.73.240.125"},
    }


async def spawn_claude_session(
    machine: str,
    prompt: str,
    working_dir: str = None,
    background: bool = False,
    model: str = None,
    timeout: int = 3600
) -> dict:
    """
    Spawn a Claude Code session on a remote machine.

    Args:
        machine: Target machine name (black, silver-fox, nvidia-spark)
        prompt: The task/prompt for Claude Code
        working_dir: Working directory on remote machine
        background: Run in background (don't wait for completion)
        model: Model override (default uses Claude's default)
        timeout: Max runtime in seconds

    Returns:
        dict with status, output, etc.
    """
    if machine not in MACHINES:
        return {"error": f"Unknown machine: {machine}", "available": list(MACHINES.keys())}

    # Build the claude command
    cmd_parts = ["claude"]

    if background:
        cmd_parts.append("--background")

    if model:
        cmd_parts.extend(["--model", model])

    # Add the prompt
    cmd_parts.extend(["--print", "--prompt", prompt])

    # Build the full command
    if working_dir:
        full_cmd = f"cd {working_dir} && {' '.join(cmd_parts)}"
    else:
        full_cmd = ' '.join(cmd_parts)

    if MESH_AVAILABLE:
        connector = MeshConnector()
        result = await connector.execute(
            machine=machine,
            command=["bash", "-c", full_cmd],
            cwd=working_dir or "/home/user",
            timeout=timeout
        )
        await connector.close()

        if result.success:
            return {
                "status": "success",
                "machine": machine,
                "method": result.method.value,
                "output": result.data
            }
        else:
            return {
                "status": "failed",
                "machine": machine,
                "error": result.error
            }
    else:
        # Fallback to direct SSH
        import subprocess

        ssh_cmd = ["ssh", machine, full_cmd]

        try:
            if background:
                # Run in background, don't wait
                proc = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                return {
                    "status": "spawned",
                    "machine": machine,
                    "pid": proc.pid,
                    "background": True
                }
            else:
                result = subprocess.run(
                    ssh_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return {
                    "status": "success" if result.returncode == 0 else "failed",
                    "machine": machine,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "machine": machine}
        except Exception as e:
            return {"status": "error", "machine": machine, "error": str(e)}


async def list_machines():
    """List available machines and their status."""
    print("\n=== Available Machines ===\n")

    if MESH_AVAILABLE:
        connector = MeshConnector()
        for name, info in MACHINES.items():
            result = await connector.health_check(name)
            status = "✓ online" if result.success else f"✗ offline ({result.error})"
            print(f"  {name:15} {info.get('tailscale_ip', 'unknown'):18} {status}")
        await connector.close()
    else:
        for name, info in MACHINES.items():
            print(f"  {name:15} {info.get('tailscale_ip', 'unknown'):18} (mesh connector not available)")

    print()


async def orchestrate_task(task: str, machines: list = None):
    """
    Orchestrate a complex task across multiple machines.

    This is the Conductor pattern - decompose a task and delegate
    to appropriate machines based on their capabilities.
    """
    machines = machines or ["black"]

    print(f"\n=== Orchestrating: {task[:50]}... ===\n")

    results = []
    for machine in machines:
        print(f"  → Spawning on {machine}...")
        result = await spawn_claude_session(machine, task, background=True)
        results.append(result)
        print(f"    Status: {result.get('status', 'unknown')}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Spawn Claude Code sessions across the mesh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s black "Fix the authentication bug in server.py"
  %(prog)s nvidia-spark "Train the model" --background
  %(prog)s --list
  %(prog)s --orchestrate "Refactor the codebase" --machines black silver-fox
"""
    )

    parser.add_argument("machine", nargs="?", help="Target machine")
    parser.add_argument("prompt", nargs="?", help="Task for Claude Code")
    parser.add_argument("--list", "-l", action="store_true", help="List available machines")
    parser.add_argument("--background", "-b", action="store_true", help="Run in background")
    parser.add_argument("--working-dir", "-w", help="Working directory on remote")
    parser.add_argument("--model", "-m", help="Model override")
    parser.add_argument("--timeout", "-t", type=int, default=3600, help="Timeout in seconds")
    parser.add_argument("--orchestrate", help="Orchestrate task across machines")
    parser.add_argument("--machines", nargs="+", help="Machines for orchestration")

    args = parser.parse_args()

    if args.list:
        asyncio.run(list_machines())
        return

    if args.orchestrate:
        results = asyncio.run(orchestrate_task(args.orchestrate, args.machines))
        print(json.dumps(results, indent=2))
        return

    if not args.machine or not args.prompt:
        parser.print_help()
        return

    result = asyncio.run(spawn_claude_session(
        machine=args.machine,
        prompt=args.prompt,
        working_dir=args.working_dir,
        background=args.background,
        model=args.model,
        timeout=args.timeout
    ))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
