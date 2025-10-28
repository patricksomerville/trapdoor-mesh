#!/usr/bin/env python3
"""Trapdoor Control Panel

Simple menu for non-technical operators to manage the local proxy, tunnels,
and connection details without juggling individual scripts.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from memory import store as memory_store
except Exception:  # pragma: no cover
    memory_store = None


REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
CONFIG_PATH = REPO_ROOT / "config" / "trapdoor.json"
RUNTIME_DIR = REPO_ROOT / ".proxy_runtime"
SESSION_PATH = RUNTIME_DIR / "session.json"
PUBLIC_URL_PATH = RUNTIME_DIR / "public_url.txt"
MEMORY_DIR = REPO_ROOT / "memory"
LESSONS_PATH = MEMORY_DIR / "lessons.jsonl"


def format_timestamp(ts: float) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    except Exception:
        return "(unknown)"


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        print("⚠️  Could not find config/trapdoor.json. Have you pulled the latest repo?", file=sys.stderr)
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_session() -> Dict[str, Any]:
    if SESSION_PATH.exists():
        try:
            return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _read_public_url() -> str:
    if PUBLIC_URL_PATH.exists():
        try:
            return PUBLIC_URL_PATH.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""


def _count_lessons() -> Optional[int]:
    if not LESSONS_PATH.exists():
        return 0
    try:
        with LESSONS_PATH.open("r", encoding="utf-8") as fh:
            return sum(1 for _ in fh)
    except Exception:
        return None


def _ping_health(port: int) -> tuple[bool, Optional[Dict[str, Any]]]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1.5) as resp:
            if resp.status != 200:
                return False, None
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return False, None


def display_status() -> None:
    cfg = load_config()
    session = read_session()
    port = cfg.get("app", {}).get("port", 8080)
    profile = session.get("profile") or cfg.get("models", {}).get("default_profile", "default")
    public_url = session.get("public_url") or _read_public_url()
    healthy, health_payload = _ping_health(port)
    model = (health_payload or {}).get("model") or session.get("model") or cfg.get("app", {}).get("model")
    lessons_count = _count_lessons()

    print("\n=========================================")
    print("Trapdoor Status")
    print("-----------------------------------------")
    proxy_state = "ONLINE" if healthy else "offline"
    icon = "🟢" if healthy else "🔴"
    print(f"Proxy: {icon} {proxy_state}  (profile: {profile}, port {port})")
    if model:
        print(f"Model: {model}")
    if healthy and health_payload:
        backend = health_payload.get("backend")
        if backend:
            print(f"Backend: {backend}")
    if public_url:
        print(f"Public URL: {public_url}")
    else:
        print("Public URL: (not published)")
    if lessons_count is not None:
        print(f"Lessons stored: {lessons_count}")
    else:
        print("Lessons stored: (unavailable)")
    print("=========================================")


def run_script(script_name: str, args: list[str] | None = None, env: Optional[Dict[str, str]] = None) -> int:
    """Execute a bash script in ./scripts with passthrough output."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"⚠️  Script missing: {script_path}")
        return 1
    cmd = ["bash", str(script_path)]
    if args:
        cmd.extend(args)
    try:
        completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env)
        return completed.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Cancelled.")
        return 130


def capture_script_output(script_name: str, args: list[str]) -> Optional[str]:
    script_path = SCRIPTS_DIR / script_name
    try:
        completed = subprocess.run(
            ["bash", str(script_path), *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except subprocess.CalledProcessError as err:
        print(err.stdout or "", end="")
        print(err.stderr or "", end="", file=sys.stderr)
        return None


def start_proxy_menu() -> None:
    print("\n🚀 Starting proxy and tunnel... This may take a moment.\n")
    code = run_script("start_proxy_and_tunnel.sh")
    if code == 0:
        session = read_session()
        public_url = session.get("public_url") or PUBLIC_URL_PATH.read_text(encoding="utf-8").strip() if PUBLIC_URL_PATH.exists() else ""
        if public_url:
            print(f"✅ Proxy is up! Public URL: {public_url}")
        else:
            print("✅ Proxy start script completed. Check logs if the tunnel URL is missing.")
    else:
        print(f"⚠️  Start script exited with code {code}. Review the output above and logs in {RUNTIME_DIR}")


def stop_services_menu() -> None:
    print("\n⏹️  Stopping proxy and tunnel processes...")
    pid_files = [
        REPO_ROOT / "server.pid",
        RUNTIME_DIR / "cloudflared.pid",
        RUNTIME_DIR / "ngrok.pid",
        RUNTIME_DIR / "ollama.pid",
    ]
    stopped = []
    for pid_file in pid_files:
        if not pid_file.exists():
            continue
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except ValueError:
            pid_file.unlink(missing_ok=True)
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            stopped.append((pid_file.name, pid))
        except ProcessLookupError:
            stopped.append((pid_file.name, pid))
        pid_file.unlink(missing_ok=True)
    if stopped:
        for name, pid in stopped:
            print(f"   • Terminated {name} (pid {pid})")
    else:
        print("   • No tracked processes were running.")
    print("Done. If tunnels were launched outside this control panel, you may still need to stop them manually.")


def ensure_token_available() -> bool:
    code = run_script("manage_auth_token.sh", ["ensure-file"])
    return code == 0


def read_token() -> Optional[str]:
    output = capture_script_output("manage_auth_token.sh", ["print"])
    return output.strip() if output else None


def show_connection_info() -> None:
    print("\n📋 Connection Instructions\n---------------------------")
    cfg = load_config()
    session = read_session()
    if not cfg:
        print("Config missing; cannot build instructions.")
        return
    if not ensure_token_available():
        print("⚠️  Unable to ensure token file. Check keychain access and try again.")
        return
    token = read_token()
    if not token:
        print("⚠️  Could not read token from keychain.")
        return
    port = session.get("port") or cfg.get("app", {}).get("port", 8080)
    public_url = ""
    if PUBLIC_URL_PATH.exists():
        public_url = PUBLIC_URL_PATH.read_text(encoding="utf-8").strip()
    system_prompt = session.get("system_prompt") or cfg.get("app", {}).get("default_system_prompt", "")
    profile = session.get("profile") or cfg.get("models", {}).get("default_profile", "default")
    model = session.get("model") or cfg.get("app", {}).get("model")

    if not public_url:
        print("⚠️  Tunnel URL not found. Start the proxy (option 1) before sharing with an external agent.\n")

    lines = [
        f"Model profile: {profile}",
        f"Model: {model}",
        f"Local health check: http://127.0.0.1:{port}/health",
    ]
    if public_url:
        lines.append(f"Public base URL: {public_url}")
    lines.append("Tools token (keep secret):")
    lines.append(f"  {token}")
    lines.append("Authorization header:")
    lines.append(f"  Authorization: Bearer {token}")
    lines.append("")
    lines.append("Recommended system prompt:")
    lines.append(textwrap.indent(system_prompt.strip() or "(not set)", "  "))
    lines.append("")
    lines.append("Quick test command:")
    if public_url:
        lines.append(f"  curl -H 'Authorization: Bearer {token}' '{public_url}/fs/ls?path=/'")
    else:
        lines.append(f"  curl -H 'Authorization: Bearer {token}' 'http://127.0.0.1:{port}/fs/ls?path=/'")

    print("\n".join(lines))
    print("\nCopy the block above into your cloud LLM interface when granting access.")


def rotate_token_menu() -> None:
    print("\n🔄 Rotating tools token...")
    code = run_script("manage_auth_token.sh", ["rotate"])
    if code == 0:
        print("✅ Token rotated. Remember to restart the proxy so new sessions use the updated token.")
    else:
        print("⚠️  Token rotation failed. Check the output above.")


def health_check_menu() -> None:
    print("\n🩺 Running health check...\n")
    code = run_script("check_health.sh")
    if code == 0:
        print("\n✅ All checks passed.")
    else:
        print("\n⚠️  Health check reported issues. Review the messages above and the logs in .proxy_runtime/")


def self_test_menu() -> None:
    print("\n🧪 Running trapdoor self-test...\n")
    code = run_script("self_test.sh")
    if code == 0:
        print("\n✅ Self-test succeeded.")
    else:
        print("\n⚠️  Self-test failed. Check the output above and ensure the proxy is running.")


def generate_access_pack_menu() -> None:
    cfg = load_config()
    if not cfg:
        print("⚠️  Missing configuration; cannot generate access pack.")
        return
    default_partner = "partner"
    partner = input(f"Partner name [{default_partner}]: ").strip() or default_partner
    default_base_url = ""
    if PUBLIC_URL_PATH.exists():
        default_base_url = PUBLIC_URL_PATH.read_text(encoding="utf-8").strip()
    if not default_base_url:
        default_base_url = cfg.get("cloudflare", {}).get("hostname", "")
        if default_base_url and not default_base_url.startswith("http"):
            default_base_url = f"https://{default_base_url}"
    base_url = input(f"Base URL [{default_base_url}]: ").strip() or default_base_url
    token_file = cfg.get("auth", {}).get("token_file", "")
    print("\n🧰 Generating access pack...")
    args = [partner]
    if base_url:
        args.append(base_url)
    if token_file:
        args.append(token_file)
    code = run_script("generate_access_pack.sh", args)
    if code == 0:
        packs_dir = (REPO_ROOT / ".proxy_runtime" / "packs")
        print(f"✅ Access pack created under {packs_dir}")
    else:
        print("⚠️  Failed to generate access pack. See the output above.")


def open_logs_menu() -> None:
    ensure_runtime_dir()
    print(f"\n🗂️  Logs and runtime files live in: {RUNTIME_DIR}")
    print("Open this folder in Finder/Explorer to inspect recent activity.")


def review_learning_menu() -> None:
    if memory_store is None:
        print("\nℹ️  Learning log module not available.")
        return
    snapshot = memory_store.describe_recent_activity()
    events = snapshot.get("events", [])[-5:]
    lessons = snapshot.get("lessons", [])[-5:]
    stats = snapshot.get("stats", {})
    print("\n🧠 Recent Learning Log\n----------------------")
    if stats:
        total = stats.get("total_events", 0)
        print(f"Logged events (last {len(events)} of {total}):")
    if not events:
        print("  • No events recorded yet. Try running the proxy and tools first.")
    else:
        for event in events:
            when = format_timestamp(event.get("ts"))
            kind = event.get("kind")
            details = event.get("data", {})
            summary = details.get("summary") or details.get("endpoint") or details.get("path") or ""
            if summary:
                summary = f" — {summary}"
            print(f"  • [{when}] {kind}{summary}")
    print("\nLessons (most recent first):")
    if not lessons:
        print("  • No lessons saved yet. Use 'Add learning note' to capture insights.")
    else:
        for lesson in lessons:
            when = format_timestamp(lesson.get("ts"))
            title = lesson.get("title", "Untitled lesson")
            summary = lesson.get("summary", "")
            tags = lesson.get("tags") or []
            tag_str = f" (tags: {', '.join(tags)})" if tags else ""
            wrapped = textwrap.fill(summary, width=68, initial_indent="      ", subsequent_indent="      ")
            print(f"  • [{when}] {title}{tag_str}\n{wrapped}")
    print("\nNote: Trapdoor automatically surfaces the most relevant recent lessons in each new Qwen session.\n")


def add_learning_note_menu() -> None:
    if memory_store is None:
        print("\nℹ️  Learning log module not available.")
        return
    print("\n✏️  Add Learning Note")
    title = input("Title (one line): ").strip()
    if not title:
        print("   • Cancelled (no title provided).")
        return
    print("Describe what Qwen should remember about this session.")
    summary = input("Summary: ").strip()
    tags_input = input("Tags (comma separated, optional): ").strip()
    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    memory_store.add_lesson(title, summary or title, tags=tags)
    print("✅ Saved. Future sessions can surface this note when searching memories.")


def main() -> None:
    ensure_runtime_dir()
    while True:
        display_status()
        print(
            textwrap.dedent(
                """
                Menu
                -----------------------------------------
                1.  Start proxy & tunnel
                2.  Stop proxy & tunnel
                3.  Show connection instructions
                4.  Rotate tools token
                5.  Run health check
                6.  Run self-test
                7.  Generate access pack
                8.  Open logs folder
                9.  Review learning log
                10. Add learning note
                11. Exit
                """
            )
        )
        choice = input("Select an option (1-11): ").strip()
        if choice == "1":
            start_proxy_menu()
        elif choice == "2":
            stop_services_menu()
        elif choice == "3":
            show_connection_info()
        elif choice == "4":
            rotate_token_menu()
        elif choice == "5":
            health_check_menu()
        elif choice == "6":
            self_test_menu()
        elif choice == "7":
            generate_access_pack_menu()
        elif choice == "8":
            open_logs_menu()
        elif choice == "9":
            review_learning_menu()
        elif choice == "10":
            add_learning_note_menu()
        elif choice == "11":
            print("Goodbye!")
            break
        else:
            print("Please enter a number between 1 and 11.")
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
