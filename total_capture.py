#!/usr/bin/env python3
"""
Total Capture System - Capture EVERYTHING

This is the unified capture layer for the Somertime mesh.
Every interaction, command, conversation, file change, and context
gets captured, indexed, and made searchable.

Capture Sources:
├── Terminal (Terminal Boss) ✅
├── Claude Code CLI (session exports) ✅
├── Claude Desktop (conversation exports)
├── ChatGPT Web (browser extension)
├── Gemini Web (browser extension)
├── Cursor AI (session logs)
├── VS Code (extension activity)
├── Git commits (all repos)
├── File changes (fswatch)
├── Clipboard history
├── Browser history
├── Screenshots (OCR'd)
├── Application usage
├── Meeting transcripts
└── Calendar events

All sources → Unified Event Stream → Memory Stack:
  - Milvus (semantic search)
  - Supermemory (cloud, 50M tokens)
  - Cipher/Qdrant (local graph)

Usage:
    python total_capture.py daemon        # Run all capture agents
    python total_capture.py status        # Check what's being captured
    python total_capture.py search "X"    # Search across everything
    python total_capture.py stats         # Capture statistics
"""

import asyncio
import json
import os
import sqlite3
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading
import queue
import time


# ==============================================================================
# Configuration
# ==============================================================================

CAPTURE_DIR = Path.home() / ".total_capture"
DB_FILE = CAPTURE_DIR / "events.db"
CONFIG_FILE = CAPTURE_DIR / "config.json"

# Default paths to watch
DEFAULT_WATCHES = {
    "claude_exports": Path.home() / ".claude" / "exports",
    "cursor_logs": Path.home() / ".cursor" / "logs",
    "downloads": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
}


class EventType(Enum):
    TERMINAL_COMMAND = "terminal_command"
    CLAUDE_SESSION = "claude_session"
    CLAUDE_DESKTOP = "claude_desktop"
    CHATGPT_WEB = "chatgpt_web"
    GEMINI_WEB = "gemini_web"
    CURSOR_SESSION = "cursor_session"
    VSCODE_ACTIVITY = "vscode_activity"
    GIT_COMMIT = "git_commit"
    FILE_CHANGE = "file_change"
    CLIPBOARD = "clipboard"
    BROWSER_HISTORY = "browser_history"
    SCREENSHOT = "screenshot"
    APP_USAGE = "app_usage"
    MEETING = "meeting"
    CALENDAR = "calendar"
    CUSTOM = "custom"


@dataclass
class CaptureEvent:
    """A single captured event."""
    id: str
    event_type: EventType
    source: str  # Machine or app name
    timestamp: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['event_type'] = d['event_type'].value
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'CaptureEvent':
        d['event_type'] = EventType(d['event_type'])
        return cls(**d)


# ==============================================================================
# Database Layer
# ==============================================================================

class CaptureDB:
    """SQLite database for captured events."""

    def __init__(self, db_path: Path = DB_FILE):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    embedding BLOB,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON events(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
                USING fts5(content, content=events, content_rowid=rowid)
            """)

    def insert(self, event: CaptureEvent) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO events
                    (id, event_type, source, timestamp, content, metadata, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id,
                    event.event_type.value,
                    event.source,
                    event.timestamp,
                    event.content,
                    json.dumps(event.metadata),
                    json.dumps(event.embedding) if event.embedding else None
                ))
                # Update FTS index
                conn.execute("""
                    INSERT INTO events_fts(rowid, content)
                    SELECT rowid, content FROM events WHERE id = ?
                """, (event.id,))
            return True
        except Exception as e:
            print(f"DB insert error: {e}")
            return False

    def search(self, query: str, limit: int = 50) -> List[CaptureEvent]:
        """Full-text search across all events."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT e.* FROM events e
                JOIN events_fts fts ON e.rowid = fts.rowid
                WHERE events_fts MATCH ?
                ORDER BY e.timestamp DESC
                LIMIT ?
            """, (query, limit)).fetchall()

            return [self._row_to_event(row) for row in rows]

    def get_recent(self, event_type: EventType = None, limit: int = 100) -> List[CaptureEvent]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if event_type:
                rows = conn.execute("""
                    SELECT * FROM events WHERE event_type = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (event_type.value, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM events ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()

            return [self._row_to_event(row) for row in rows]

    def stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            by_type = dict(conn.execute("""
                SELECT event_type, COUNT(*) FROM events GROUP BY event_type
            """).fetchall())
            by_source = dict(conn.execute("""
                SELECT source, COUNT(*) FROM events GROUP BY source
            """).fetchall())
            oldest = conn.execute("SELECT MIN(timestamp) FROM events").fetchone()[0]
            newest = conn.execute("SELECT MAX(timestamp) FROM events").fetchone()[0]

            return {
                "total_events": total,
                "by_type": by_type,
                "by_source": by_source,
                "oldest": oldest,
                "newest": newest,
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
            }

    def _row_to_event(self, row) -> CaptureEvent:
        return CaptureEvent(
            id=row['id'],
            event_type=EventType(row['event_type']),
            source=row['source'],
            timestamp=row['timestamp'],
            content=row['content'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            embedding=json.loads(row['embedding']) if row['embedding'] else None
        )


# ==============================================================================
# Capture Agents
# ==============================================================================

class CaptureAgent:
    """Base class for capture agents."""

    def __init__(self, db: CaptureDB, source: str):
        self.db = db
        self.source = source
        self.running = False
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        raise NotImplementedError

    def _create_event(self, event_type: EventType, content: str,
                      metadata: Dict = None) -> CaptureEvent:
        event_id = hashlib.sha256(
            f"{event_type.value}:{self.source}:{content}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        return CaptureEvent(
            id=event_id,
            event_type=event_type,
            source=self.source,
            timestamp=datetime.now().isoformat(),
            content=content,
            metadata=metadata or {}
        )


class ClipboardAgent(CaptureAgent):
    """Captures clipboard changes."""

    def __init__(self, db: CaptureDB):
        super().__init__(db, "clipboard")
        self.last_content = ""

    def _run(self):
        while self.running:
            try:
                # macOS clipboard
                result = subprocess.run(
                    ["pbpaste"], capture_output=True, text=True, timeout=1
                )
                content = result.stdout.strip()

                if content and content != self.last_content:
                    self.last_content = content
                    # Only capture if it's substantial
                    if len(content) > 10:
                        event = self._create_event(
                            EventType.CLIPBOARD,
                            content[:5000],  # Limit size
                            {"length": len(content)}
                        )
                        self.db.insert(event)

            except Exception as e:
                pass  # Silently continue

            time.sleep(1)  # Check every second


class GitWatcherAgent(CaptureAgent):
    """Watches git repos for commits."""

    def __init__(self, db: CaptureDB, repo_paths: List[Path]):
        super().__init__(db, "git")
        self.repo_paths = repo_paths
        self.seen_commits = set()

    def _run(self):
        while self.running:
            for repo_path in self.repo_paths:
                try:
                    self._check_repo(repo_path)
                except Exception as e:
                    pass

            time.sleep(30)  # Check every 30 seconds

    def _check_repo(self, repo_path: Path):
        if not (repo_path / ".git").exists():
            return

        result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            commit_hash = line.split()[0]
            if commit_hash not in self.seen_commits:
                self.seen_commits.add(commit_hash)

                # Get full commit info
                detail = subprocess.run(
                    ["git", "show", "--stat", commit_hash],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                event = self._create_event(
                    EventType.GIT_COMMIT,
                    detail.stdout[:5000],
                    {"repo": str(repo_path), "commit": commit_hash}
                )
                self.db.insert(event)


class FileWatcherAgent(CaptureAgent):
    """Watches directories for file changes."""

    def __init__(self, db: CaptureDB, watch_paths: Dict[str, Path]):
        super().__init__(db, "filesystem")
        self.watch_paths = watch_paths
        self.file_mtimes = {}

    def _run(self):
        while self.running:
            for name, path in self.watch_paths.items():
                try:
                    self._scan_directory(name, path)
                except Exception as e:
                    pass

            time.sleep(10)  # Scan every 10 seconds

    def _scan_directory(self, name: str, path: Path):
        if not path.exists():
            return

        for file in path.rglob("*"):
            if file.is_file() and not file.name.startswith('.'):
                try:
                    mtime = file.stat().st_mtime
                    key = str(file)

                    if key not in self.file_mtimes:
                        self.file_mtimes[key] = mtime
                    elif mtime > self.file_mtimes[key]:
                        self.file_mtimes[key] = mtime

                        # File was modified
                        event = self._create_event(
                            EventType.FILE_CHANGE,
                            f"Modified: {file.name}",
                            {
                                "path": str(file),
                                "watch_name": name,
                                "size": file.stat().st_size,
                                "suffix": file.suffix
                            }
                        )
                        self.db.insert(event)

                except Exception:
                    pass


class AppUsageAgent(CaptureAgent):
    """Tracks active application usage (macOS)."""

    def __init__(self, db: CaptureDB):
        super().__init__(db, "app_usage")
        self.last_app = ""

    def _run(self):
        while self.running:
            try:
                # Get frontmost app on macOS
                script = '''
                    tell application "System Events"
                        set frontApp to name of first application process whose frontmost is true
                    end tell
                    return frontApp
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True, text=True, timeout=5
                )
                app_name = result.stdout.strip()

                if app_name and app_name != self.last_app:
                    self.last_app = app_name
                    event = self._create_event(
                        EventType.APP_USAGE,
                        f"Switched to: {app_name}",
                        {"app": app_name}
                    )
                    self.db.insert(event)

            except Exception:
                pass

            time.sleep(5)  # Check every 5 seconds


class ClaudeExportAgent(CaptureAgent):
    """Watches for Claude session exports."""

    def __init__(self, db: CaptureDB, export_path: Path):
        super().__init__(db, "claude_exports")
        self.export_path = export_path
        self.seen_files = set()

    def _run(self):
        while self.running:
            try:
                if self.export_path.exists():
                    for file in self.export_path.glob("*.md"):
                        if str(file) not in self.seen_files:
                            self.seen_files.add(str(file))
                            self._ingest_export(file)

                    for file in self.export_path.glob("*.json"):
                        if str(file) not in self.seen_files:
                            self.seen_files.add(str(file))
                            self._ingest_export(file)

            except Exception as e:
                print(f"Claude export error: {e}")

            time.sleep(30)

    def _ingest_export(self, file: Path):
        try:
            content = file.read_text()[:50000]  # Limit size
            event = self._create_event(
                EventType.CLAUDE_SESSION,
                content,
                {
                    "filename": file.name,
                    "path": str(file),
                    "size": file.stat().st_size
                }
            )
            self.db.insert(event)
            print(f"  Ingested: {file.name}")
        except Exception as e:
            print(f"  Failed to ingest {file.name}: {e}")


class BrowserHistoryAgent(CaptureAgent):
    """Captures browser history (Chrome/Safari on macOS)."""

    def __init__(self, db: CaptureDB):
        super().__init__(db, "browser")
        self.last_check = datetime.now() - timedelta(hours=1)

    def _run(self):
        while self.running:
            try:
                self._capture_chrome_history()
            except Exception:
                pass

            time.sleep(300)  # Every 5 minutes

    def _capture_chrome_history(self):
        history_path = Path.home() / "Library/Application Support/Google/Chrome/Default/History"

        if not history_path.exists():
            return

        # Copy to temp file (Chrome locks the DB)
        import shutil
        temp_path = CAPTURE_DIR / "chrome_history_temp.db"
        shutil.copy2(history_path, temp_path)

        try:
            conn = sqlite3.connect(temp_path)
            # Chrome stores time as microseconds since Jan 1, 1601
            chrome_epoch = datetime(1601, 1, 1)
            cutoff = (self.last_check - chrome_epoch).total_seconds() * 1000000

            rows = conn.execute("""
                SELECT url, title, visit_count, last_visit_time
                FROM urls
                WHERE last_visit_time > ?
                ORDER BY last_visit_time DESC
                LIMIT 100
            """, (cutoff,)).fetchall()

            for url, title, count, visit_time in rows:
                event = self._create_event(
                    EventType.BROWSER_HISTORY,
                    f"{title}\n{url}",
                    {"url": url, "title": title, "visits": count}
                )
                self.db.insert(event)

            self.last_check = datetime.now()
            conn.close()
        finally:
            temp_path.unlink(missing_ok=True)


# ==============================================================================
# Memory Sync (to Milvus/Supermemory)
# ==============================================================================

class MemorySyncer:
    """Syncs captured events to long-term memory systems."""

    def __init__(self, db: CaptureDB):
        self.db = db
        self.last_sync = None

    async def sync_to_supermemory(self, api_key: str, since: datetime = None):
        """Sync events to Supermemory."""
        try:
            from supermemory_bridge import SupermemoryBridge
            bridge = SupermemoryBridge(api_key)

            events = self.db.get_recent(limit=1000)
            synced = 0

            for event in events:
                if since and datetime.fromisoformat(event.timestamp) < since:
                    continue

                memory_id = bridge.add_memory(
                    content=event.content,
                    source=f"total_capture:{event.source}",
                    tags=[event.event_type.value, event.source],
                    metadata=event.metadata
                )

                if memory_id:
                    synced += 1

            bridge.close()
            return synced

        except ImportError:
            print("Supermemory bridge not available")
            return 0

    async def sync_to_milvus(self, host: str = "localhost", port: int = 19530):
        """Sync events to Milvus."""
        # TODO: Implement Milvus sync
        pass


# ==============================================================================
# Main Controller
# ==============================================================================

class TotalCapture:
    """Main controller for the total capture system."""

    def __init__(self):
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        self.db = CaptureDB()
        self.agents: List[CaptureAgent] = []
        self.syncer = MemorySyncer(self.db)

    def start_all_agents(self, config: Dict = None):
        """Start all capture agents."""
        config = config or {}

        print("\n🔴 TOTAL CAPTURE SYSTEM")
        print("   Capturing everything...\n")

        # Clipboard
        if config.get("clipboard", True):
            agent = ClipboardAgent(self.db)
            agent.start()
            self.agents.append(agent)
            print("   ✓ Clipboard agent started")

        # App usage
        if config.get("app_usage", True):
            agent = AppUsageAgent(self.db)
            agent.start()
            self.agents.append(agent)
            print("   ✓ App usage agent started")

        # Git repos
        git_repos = config.get("git_repos", [
            Path.home() / "Projects",
            Path.home() / "Desktop" / "Trapdoor",
        ])
        if git_repos:
            agent = GitWatcherAgent(self.db, [Path(p) for p in git_repos])
            agent.start()
            self.agents.append(agent)
            print(f"   ✓ Git watcher started ({len(git_repos)} repos)")

        # File watcher
        watch_paths = config.get("watch_paths", DEFAULT_WATCHES)
        if watch_paths:
            agent = FileWatcherAgent(self.db, {k: Path(v) for k, v in watch_paths.items()})
            agent.start()
            self.agents.append(agent)
            print(f"   ✓ File watcher started ({len(watch_paths)} paths)")

        # Claude exports
        claude_export_path = config.get("claude_exports", Path.home() / ".claude" / "exports")
        if claude_export_path:
            agent = ClaudeExportAgent(self.db, Path(claude_export_path))
            agent.start()
            self.agents.append(agent)
            print("   ✓ Claude export agent started")

        # Browser history
        if config.get("browser_history", True):
            agent = BrowserHistoryAgent(self.db)
            agent.start()
            self.agents.append(agent)
            print("   ✓ Browser history agent started")

        print(f"\n   Total agents: {len(self.agents)}")
        print("   Press Ctrl+C to stop\n")

    def stop_all_agents(self):
        print("\nStopping agents...")
        for agent in self.agents:
            agent.stop()
        print("All agents stopped.")

    def run_daemon(self):
        """Run as daemon, capturing continuously."""
        self.start_all_agents()

        try:
            while True:
                time.sleep(60)
                stats = self.db.stats()
                print(f"   📊 Captured: {stats['total_events']} events")
        except KeyboardInterrupt:
            self.stop_all_agents()


# ==============================================================================
# CLI
# ==============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Total Capture System")
    subparsers = parser.add_subparsers(dest="command")

    # Daemon
    subparsers.add_parser("daemon", help="Run capture daemon")

    # Status
    subparsers.add_parser("status", help="Show capture status")

    # Search
    search_parser = subparsers.add_parser("search", help="Search captured events")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=20)

    # Recent
    recent_parser = subparsers.add_parser("recent", help="Show recent events")
    recent_parser.add_argument("--type", help="Filter by event type")
    recent_parser.add_argument("--limit", type=int, default=20)

    # Stats
    subparsers.add_parser("stats", help="Show capture statistics")

    # Sync
    sync_parser = subparsers.add_parser("sync", help="Sync to memory systems")
    sync_parser.add_argument("--supermemory", help="Supermemory API key")

    args = parser.parse_args()

    capture = TotalCapture()

    if args.command == "daemon":
        capture.run_daemon()

    elif args.command == "status":
        print("\n📊 CAPTURE STATUS\n")
        stats = capture.db.stats()
        print(f"   Total events: {stats['total_events']}")
        print(f"   Database size: {stats['db_size_mb']} MB")
        print(f"   Oldest: {stats['oldest']}")
        print(f"   Newest: {stats['newest']}")
        print("\n   By type:")
        for t, count in stats['by_type'].items():
            print(f"      {t}: {count}")
        print()

    elif args.command == "search":
        results = capture.db.search(args.query, limit=args.limit)
        print(f"\n🔍 Search: '{args.query}' ({len(results)} results)\n")
        for event in results:
            print(f"   [{event.event_type.value}] {event.timestamp}")
            print(f"   {event.content[:100]}...")
            print()

    elif args.command == "recent":
        event_type = EventType(args.type) if args.type else None
        results = capture.db.get_recent(event_type, limit=args.limit)
        print(f"\n📋 Recent events ({len(results)})\n")
        for event in results:
            print(f"   [{event.event_type.value}] {event.source} @ {event.timestamp}")
            print(f"   {event.content[:80]}...")
            print()

    elif args.command == "stats":
        stats = capture.db.stats()
        print(json.dumps(stats, indent=2))

    elif args.command == "sync":
        if args.supermemory:
            import asyncio
            count = asyncio.run(capture.syncer.sync_to_supermemory(args.supermemory))
            print(f"Synced {count} events to Supermemory")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
