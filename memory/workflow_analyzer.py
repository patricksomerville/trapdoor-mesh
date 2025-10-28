#!/usr/bin/env python3
"""
Analyze workflow patterns and suggest optimizations
"""
from __future__ import annotations
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Add parent directory to path to import store
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import store


def analyze_workflows():
    """Generate workflow analytics"""

    # Load all events (we'll identify workflows from sequences)
    events = list(store._load_jsonl(store.EVENTS_PATH))

    if not events:
        print("No events found in memory system yet.")
        return

    print(f"=== Total Events: {len(events)} ===\n")

    # 1. Event type distribution
    event_types = Counter(e.get("kind") for e in events)
    print("=== Event Type Distribution ===")
    for kind, count in event_types.most_common():
        print(f"{count:3d}x {kind}")

    # 2. Identify command sequences (potential workflows)
    print("\n=== Common Command Sequences ===")
    sequences = []
    current_seq = []

    for e in events:
        kind = e.get("kind")
        if kind in ["fs_read", "fs_ls", "exec", "fs_write"]:
            current_seq.append(kind)
            if len(current_seq) >= 2:
                sequences.append(tuple(current_seq[-3:]))  # Last 3 commands

    if sequences:
        seq_counts = Counter(sequences)
        for seq, count in seq_counts.most_common(10):
            if count > 1:  # Only show repeated patterns
                print(f"{count:3d}x {' → '.join(seq)}")
    else:
        print("No repeated sequences found yet.")

    # 3. Most accessed paths
    print("\n=== Most Accessed Paths ===")
    paths = []
    for e in events:
        data = e.get("data", {})
        if "path" in data:
            paths.append(data["path"])

    if paths:
        path_counts = Counter(paths)
        for path, count in path_counts.most_common(10):
            print(f"{count:3d}x {path}")
    else:
        print("No file access patterns yet.")

    # 4. Command execution patterns
    print("\n=== Command Execution Patterns ===")
    commands = []
    for e in events:
        if e.get("kind") == "exec":
            cmd = e.get("data", {}).get("cmd", [])
            if cmd:
                commands.append(cmd[0] if isinstance(cmd, list) else str(cmd))

    if commands:
        cmd_counts = Counter(commands)
        for cmd, count in cmd_counts.most_common(10):
            print(f"{count:3d}x {cmd}")
    else:
        print("No command execution patterns yet.")

    # 5. Chat completion frequency
    chat_events = [e for e in events if e.get("kind") == "chat_completion"]
    print(f"\n=== Chat Completions: {len(chat_events)} ===")

    if chat_events:
        # Show recent chat summaries
        print("\nRecent chats:")
        for e in chat_events[-5:]:
            summary = e.get("data", {}).get("summary", "")[:60]
            print(f"  - {summary}")

    # 6. Automation candidates
    print("\n=== Potential Automation Candidates ===")

    # Find repeated fs_read operations
    read_paths = [e.get("data", {}).get("path") for e in events
                  if e.get("kind") == "fs_read"]
    read_counts = Counter(p for p in read_paths if p)

    if read_counts:
        print("\nFrequently read files:")
        for path, count in read_counts.most_common(5):
            if count >= 2:
                print(f"  {count:3d}x {path}")
                print(f"      → Could cache or auto-include in context")

    # Find repeated command sequences
    if sequences:
        print("\nRepeated command sequences:")
        for seq, count in seq_counts.most_common(5):
            if count >= 3:
                print(f"  {count:3d}x {' → '.join(seq)}")
                print(f"      → Could create workflow shortcut")

    # 7. Time analysis
    print("\n=== Activity Timeline ===")
    if events:
        # Extract timestamps safely (events have different structures)
        def get_ts(event):
            return event.get("ts") or event.get("data", {}).get("ts", 0)

        first_ts = get_ts(events[0])
        last_ts = get_ts(events[-1])

        if first_ts and last_ts and last_ts > first_ts:
            duration_hours = (last_ts - first_ts) / 3600
            print(f"Time span: {duration_hours:.1f} hours")
            print(f"Events per hour: {len(events) / duration_hours:.1f}")
        else:
            print("Insufficient timestamp data for timeline analysis")

    print("\n" + "="*50)
    print("Analysis complete!")
    print("\nNext steps:")
    print("1. Identify workflows you repeat often")
    print("2. Implement workflow tracking in local_agent_server.py")
    print("3. Watch Qwen learn from your patterns!")


if __name__ == "__main__":
    try:
        analyze_workflows()
    except Exception as e:
        print(f"Error analyzing workflows: {e}")
        import traceback
        traceback.print_exc()
