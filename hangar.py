#!/usr/bin/env python3
"""
The Hangar - Fleet Spawning System for Claude Code

A folder tree structure where each directory with a CLAUDE.md becomes
a "bay" that can launch a Claude instance. The Conductor can spin up
multiple Claude Haiku instances simultaneously as a fleet.

Structure:
    hangar/
    ├── CLAUDE.md           # Hangar-level instructions
    ├── bay_01_frontend/
    │   ├── CLAUDE.md       # Frontend specialist instructions
    │   └── context/        # Relevant files for this bay
    ├── bay_02_backend/
    │   ├── CLAUDE.md       # Backend specialist instructions
    │   └── context/
    ├── bay_03_testing/
    │   ├── CLAUDE.md       # Testing specialist instructions
    │   └── context/
    └── bay_04_docs/
        ├── CLAUDE.md       # Documentation specialist
        └── context/

Usage:
    python hangar.py launch --all          # Launch all bays
    python hangar.py launch bay_01 bay_02  # Launch specific bays
    python hangar.py status                # Check fleet status
    python hangar.py collect               # Gather results from all bays
"""

import asyncio
import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse


# ==============================================================================
# Configuration
# ==============================================================================

HANGAR_DIR = Path.home() / ".hangar"
STATE_FILE = HANGAR_DIR / "fleet_state.json"
DEFAULT_MODEL = "haiku"  # Fast and cheap for parallel work


@dataclass
class Bay:
    """A single bay in the hangar."""
    name: str
    path: Path
    claude_md: Path
    status: str = "idle"  # idle, launching, running, completed, failed
    pid: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output_file: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['path'] = str(d['path'])
        d['claude_md'] = str(d['claude_md'])
        return d


@dataclass
class FleetState:
    """State of the entire fleet."""
    hangar_path: str
    mission: str
    launched_at: str
    bays: List[Bay]

    def to_dict(self) -> Dict:
        return {
            "hangar_path": self.hangar_path,
            "mission": self.mission,
            "launched_at": self.launched_at,
            "bays": [b.to_dict() for b in self.bays]
        }


# ==============================================================================
# Bay Discovery
# ==============================================================================

def discover_bays(hangar_path: Path) -> List[Bay]:
    """
    Discover all bays in the hangar.
    A bay is any subdirectory containing a CLAUDE.md file.
    """
    bays = []

    for item in sorted(hangar_path.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            claude_md = item / "CLAUDE.md"
            if claude_md.exists():
                bays.append(Bay(
                    name=item.name,
                    path=item,
                    claude_md=claude_md
                ))

    return bays


def read_bay_instructions(bay: Bay) -> str:
    """Read the CLAUDE.md instructions for a bay."""
    return bay.claude_md.read_text()


# ==============================================================================
# Fleet Operations
# ==============================================================================

def launch_single_bay(
    bay: Bay,
    mission: str,
    model: str = DEFAULT_MODEL,
    timeout: int = 600
) -> Bay:
    """
    Launch Claude Code in a single bay.

    Returns updated Bay with status.
    """
    bay.status = "launching"
    bay.started_at = datetime.now().isoformat()

    # Create output file for this bay
    output_file = HANGAR_DIR / f"{bay.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    bay.output_file = str(output_file)

    # Build the prompt combining bay instructions + mission
    bay_instructions = read_bay_instructions(bay)
    full_prompt = f"""# Bay Instructions
{bay_instructions}

# Current Mission
{mission}

# Output
Complete your assigned portion of the mission. Be thorough but focused on your specialty."""

    # Build command
    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model", model,
        "--prompt", full_prompt
    ]

    try:
        bay.status = "running"

        with open(output_file, 'w') as f:
            result = subprocess.run(
                cmd,
                cwd=str(bay.path),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            f.write(f"=== Bay: {bay.name} ===\n")
            f.write(f"Started: {bay.started_at}\n")
            f.write(f"Model: {model}\n")
            f.write(f"Working Dir: {bay.path}\n")
            f.write(f"\n=== STDOUT ===\n{result.stdout}\n")
            if result.stderr:
                f.write(f"\n=== STDERR ===\n{result.stderr}\n")
            f.write(f"\n=== Return Code: {result.returncode} ===\n")

        bay.status = "completed" if result.returncode == 0 else "failed"
        bay.completed_at = datetime.now().isoformat()

        if result.returncode != 0:
            bay.error = result.stderr[:500] if result.stderr else "Non-zero exit"

    except subprocess.TimeoutExpired:
        bay.status = "failed"
        bay.error = f"Timeout after {timeout}s"
        bay.completed_at = datetime.now().isoformat()
    except Exception as e:
        bay.status = "failed"
        bay.error = str(e)
        bay.completed_at = datetime.now().isoformat()

    return bay


def launch_fleet(
    hangar_path: Path,
    mission: str,
    bay_names: Optional[List[str]] = None,
    model: str = DEFAULT_MODEL,
    max_parallel: int = 10,
    timeout: int = 600
) -> FleetState:
    """
    Launch the fleet - spawn Claude instances in parallel.

    Args:
        hangar_path: Path to the hangar directory
        mission: The overall mission/task
        bay_names: Specific bays to launch (None = all)
        model: Model to use (default: haiku for speed)
        max_parallel: Max concurrent launches
        timeout: Per-bay timeout in seconds

    Returns:
        FleetState with results
    """
    # Ensure state directory exists
    HANGAR_DIR.mkdir(parents=True, exist_ok=True)

    # Discover bays
    all_bays = discover_bays(hangar_path)

    # Filter to requested bays
    if bay_names:
        bays = [b for b in all_bays if b.name in bay_names]
    else:
        bays = all_bays

    if not bays:
        print("No bays found!")
        return None

    print(f"\n🚀 LAUNCHING FLEET")
    print(f"   Hangar: {hangar_path}")
    print(f"   Mission: {mission[:60]}...")
    print(f"   Bays: {len(bays)}")
    print(f"   Model: {model}")
    print(f"   Parallel: {max_parallel}")
    print()

    # Launch in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = {
            executor.submit(launch_single_bay, bay, mission, model, timeout): bay
            for bay in bays
        }

        for future in as_completed(futures):
            bay = futures[future]
            try:
                updated_bay = future.result()
                idx = next(i for i, b in enumerate(bays) if b.name == updated_bay.name)
                bays[idx] = updated_bay

                status_icon = "✓" if updated_bay.status == "completed" else "✗"
                print(f"   {status_icon} {updated_bay.name}: {updated_bay.status}")
            except Exception as e:
                print(f"   ✗ {bay.name}: Exception - {e}")

    # Create fleet state
    state = FleetState(
        hangar_path=str(hangar_path),
        mission=mission,
        launched_at=datetime.now().isoformat(),
        bays=bays
    )

    # Save state
    STATE_FILE.write_text(json.dumps(state.to_dict(), indent=2))

    # Summary
    completed = sum(1 for b in bays if b.status == "completed")
    failed = sum(1 for b in bays if b.status == "failed")

    print(f"\n📊 FLEET STATUS")
    print(f"   Completed: {completed}/{len(bays)}")
    print(f"   Failed: {failed}/{len(bays)}")
    print(f"   State saved: {STATE_FILE}")

    return state


def collect_results(state: FleetState) -> str:
    """
    Collect and combine results from all bays.

    Returns combined output as a single document.
    """
    results = []
    results.append(f"# Fleet Results")
    results.append(f"Mission: {state.mission}")
    results.append(f"Launched: {state.launched_at}")
    results.append("")

    for bay in state.bays:
        results.append(f"## {bay.name}")
        results.append(f"Status: {bay.status}")

        if bay.output_file and Path(bay.output_file).exists():
            output = Path(bay.output_file).read_text()
            # Extract just the stdout portion
            if "=== STDOUT ===" in output:
                stdout = output.split("=== STDOUT ===")[1]
                if "=== STDERR ===" in stdout:
                    stdout = stdout.split("=== STDERR ===")[0]
                elif "=== Return Code" in stdout:
                    stdout = stdout.split("=== Return Code")[0]
                results.append(stdout.strip())
        elif bay.error:
            results.append(f"Error: {bay.error}")

        results.append("")

    return "\n".join(results)


# ==============================================================================
# Hangar Initialization
# ==============================================================================

def init_hangar(path: Path, template: str = "default"):
    """
    Initialize a new hangar with template bays.

    Templates:
    - default: frontend, backend, testing, docs
    - fullstack: frontend, backend, api, database, testing, docs, devops
    - research: literature, analysis, synthesis, writing
    """
    templates = {
        "default": [
            ("bay_01_frontend", "You are a frontend specialist. Focus on UI, UX, React/Vue components, CSS, and client-side logic."),
            ("bay_02_backend", "You are a backend specialist. Focus on server logic, APIs, databases, and system architecture."),
            ("bay_03_testing", "You are a testing specialist. Focus on unit tests, integration tests, and quality assurance."),
            ("bay_04_docs", "You are a documentation specialist. Focus on README files, API docs, and user guides."),
        ],
        "fullstack": [
            ("bay_01_frontend", "Frontend specialist: React/Vue, CSS, UI/UX, client-side state management."),
            ("bay_02_backend", "Backend specialist: Node/Python/Go, business logic, server architecture."),
            ("bay_03_api", "API specialist: REST/GraphQL design, endpoint implementation, validation."),
            ("bay_04_database", "Database specialist: Schema design, queries, migrations, optimization."),
            ("bay_05_testing", "Testing specialist: Unit tests, integration tests, E2E tests."),
            ("bay_06_docs", "Documentation specialist: README, API docs, architecture diagrams."),
            ("bay_07_devops", "DevOps specialist: CI/CD, Docker, deployment, monitoring."),
        ],
        "research": [
            ("bay_01_literature", "Literature review specialist. Find and summarize relevant prior work."),
            ("bay_02_analysis", "Analysis specialist. Break down problems, identify patterns, extract insights."),
            ("bay_03_synthesis", "Synthesis specialist. Combine findings into coherent conclusions."),
            ("bay_04_writing", "Writing specialist. Create clear, well-structured documents."),
        ],
    }

    if template not in templates:
        print(f"Unknown template: {template}")
        print(f"Available: {list(templates.keys())}")
        return

    path.mkdir(parents=True, exist_ok=True)

    # Create hangar-level CLAUDE.md
    hangar_md = path / "CLAUDE.md"
    hangar_md.write_text(f"""# The Hangar

This is a fleet spawning system. Each bay below contains a specialist Claude instance.

## Bays
{chr(10).join(f"- {name}" for name, _ in templates[template])}

## How It Works
When a mission is launched, all bays receive the mission brief and work in parallel.
Each bay focuses on its specialty, contributing its part to the overall goal.

## Template: {template}
""")

    # Create bays
    for bay_name, instructions in templates[template]:
        bay_path = path / bay_name
        bay_path.mkdir(exist_ok=True)

        claude_md = bay_path / "CLAUDE.md"
        claude_md.write_text(f"""# {bay_name.replace('_', ' ').title()}

{instructions}

## Your Role
You are part of a fleet working on a shared mission. Focus on your specialty.
Be thorough but concise. Your output will be combined with other specialists.

## Working Directory
All relevant files for your work are in this directory or its subdirectories.
""")

        # Create context directory
        (bay_path / "context").mkdir(exist_ok=True)

    print(f"✓ Initialized hangar at {path}")
    print(f"  Template: {template}")
    print(f"  Bays: {len(templates[template])}")


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="The Hangar - Fleet Spawning System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init ~/my_hangar                    # Initialize with default template
  %(prog)s init ~/my_hangar --template fullstack
  %(prog)s launch ~/my_hangar "Build a REST API"
  %(prog)s launch ~/my_hangar "Fix all bugs" --bays bay_01 bay_03
  %(prog)s status
  %(prog)s collect > results.md
"""
    )

    subparsers = parser.add_subparsers(dest="command")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new hangar")
    init_parser.add_argument("path", type=Path, help="Path for the hangar")
    init_parser.add_argument("--template", "-t", default="default",
                            choices=["default", "fullstack", "research"],
                            help="Template to use")

    # Launch command
    launch_parser = subparsers.add_parser("launch", help="Launch the fleet")
    launch_parser.add_argument("path", type=Path, help="Path to hangar")
    launch_parser.add_argument("mission", help="Mission/task for the fleet")
    launch_parser.add_argument("--bays", "-b", nargs="+", help="Specific bays to launch")
    launch_parser.add_argument("--model", "-m", default="haiku", help="Model (default: haiku)")
    launch_parser.add_argument("--parallel", "-p", type=int, default=10, help="Max parallel")
    launch_parser.add_argument("--timeout", type=int, default=600, help="Per-bay timeout")

    # Status command
    subparsers.add_parser("status", help="Show fleet status")

    # Collect command
    subparsers.add_parser("collect", help="Collect results from all bays")

    # List command
    list_parser = subparsers.add_parser("list", help="List bays in a hangar")
    list_parser.add_argument("path", type=Path, help="Path to hangar")

    args = parser.parse_args()

    if args.command == "init":
        init_hangar(args.path, args.template)

    elif args.command == "launch":
        if not args.path.exists():
            print(f"Hangar not found: {args.path}")
            sys.exit(1)

        launch_fleet(
            hangar_path=args.path,
            mission=args.mission,
            bay_names=args.bays,
            model=args.model,
            max_parallel=args.parallel,
            timeout=args.timeout
        )

    elif args.command == "status":
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
            print(json.dumps(state, indent=2))
        else:
            print("No fleet state found. Launch a fleet first.")

    elif args.command == "collect":
        if STATE_FILE.exists():
            state_dict = json.loads(STATE_FILE.read_text())
            # Reconstruct FleetState
            bays = [Bay(**{k: Path(v) if k in ['path', 'claude_md'] else v
                          for k, v in b.items()}) for b in state_dict['bays']]
            state = FleetState(
                hangar_path=state_dict['hangar_path'],
                mission=state_dict['mission'],
                launched_at=state_dict['launched_at'],
                bays=bays
            )
            print(collect_results(state))
        else:
            print("No fleet state found. Launch a fleet first.")

    elif args.command == "list":
        if not args.path.exists():
            print(f"Hangar not found: {args.path}")
            sys.exit(1)

        bays = discover_bays(args.path)
        print(f"\nBays in {args.path}:\n")
        for bay in bays:
            print(f"  📦 {bay.name}")
            # Show first line of CLAUDE.md
            first_line = read_bay_instructions(bay).split('\n')[0]
            print(f"     {first_line[:60]}...")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
