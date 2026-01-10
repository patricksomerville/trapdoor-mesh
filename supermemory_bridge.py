#!/usr/bin/env python3
"""
Supermemory Bridge - Long-term memory for the Trapdoor mesh

Supermemory is "The Memory API for the AI era" - providing persistent,
scalable memory across all AI interactions. This bridges it to trapdoor.

Memory Layers (now unified):
- Cipher/Qdrant: Local semantic search (fast, private)
- Supermemory: Cloud long-term memory (50M tokens/user, global)
- Milvus: Terminal history search (command patterns)

Usage:
    # Store a memory
    python supermemory_bridge.py add "How to fix the auth bug in trapdoor"

    # Search memories
    python supermemory_bridge.py search "authentication issues"

    # Sync from local events
    python supermemory_bridge.py sync

    # As a library
    from supermemory_bridge import SupermemoryBridge
    bridge = SupermemoryBridge()
    bridge.add_memory("Important insight about X")
    results = bridge.search("X related topics")
"""

import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


# ==============================================================================
# Configuration
# ==============================================================================

# API Configuration
SUPERMEMORY_API_URL = "https://api.supermemory.ai/v3"
SUPERMEMORY_API_KEY = os.getenv("SUPERMEMORY_API_KEY", "")

# Local config file for API key
CONFIG_FILE = Path.home() / ".trapdoor" / "supermemory.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key() -> str:
    """Get API key from env or config file."""
    if SUPERMEMORY_API_KEY:
        return SUPERMEMORY_API_KEY
    config = load_config()
    return config.get("api_key", "")


# ==============================================================================
# Data Models
# ==============================================================================

@dataclass
class Memory:
    """A memory entry."""
    id: str
    content: str
    source: str
    tags: List[str]
    created_at: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SearchResult:
    """A search result."""
    memory: Memory
    score: float
    snippet: str

    def to_dict(self) -> Dict:
        return {
            "memory": self.memory.to_dict(),
            "score": self.score,
            "snippet": self.snippet
        }


# ==============================================================================
# Supermemory Bridge
# ==============================================================================

class SupermemoryBridge:
    """
    Bridge to Supermemory API.

    Provides long-term memory storage and retrieval with semantic search.
    Scales to 50M tokens per user.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.base_url = SUPERMEMORY_API_URL
        self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._client

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def add_memory(
        self,
        content: str,
        source: str = "trapdoor",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default"
    ) -> Optional[str]:
        """
        Add a memory to Supermemory.

        Args:
            content: The text content to store
            source: Origin identifier (e.g., "trapdoor", "claude", "hangar")
            tags: Optional tags for filtering
            metadata: Optional additional metadata
            user_id: User identifier for multi-user setups

        Returns:
            Memory ID if successful
        """
        if not self.configured:
            print("Warning: Supermemory API key not configured")
            return None

        payload = {
            "content": content,
            "metadata": {
                "source": source,
                "tags": tags or [],
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
        }

        try:
            # Using the memories/add endpoint
            response = self.client.post(
                f"{self.base_url}/memories",
                json=payload,
                params={"userId": user_id}
            )

            if response.status_code in (200, 201):
                data = response.json()
                return data.get("id") or data.get("memoryId")
            else:
                print(f"Add memory failed: {response.status_code} - {response.text[:200]}")
                return None

        except Exception as e:
            print(f"Add memory error: {e}")
            return None

    def search(
        self,
        query: str,
        limit: int = 10,
        user_id: str = "default",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search memories semantically.

        Args:
            query: Natural language search query
            limit: Max results to return
            user_id: User identifier
            filters: Optional metadata filters

        Returns:
            List of SearchResult objects
        """
        if not self.configured:
            print("Warning: Supermemory API key not configured")
            return []

        try:
            response = self.client.post(
                f"{self.base_url}/search",
                json={
                    "query": query,
                    "topK": limit,
                    "filters": filters or {}
                },
                params={"userId": user_id}
            )

            if response.status_code == 200:
                data = response.json()
                results = []

                for item in data.get("results", data.get("memories", [])):
                    memory = Memory(
                        id=item.get("id", ""),
                        content=item.get("content", item.get("text", "")),
                        source=item.get("metadata", {}).get("source", "unknown"),
                        tags=item.get("metadata", {}).get("tags", []),
                        created_at=item.get("createdAt", item.get("metadata", {}).get("timestamp", "")),
                        metadata=item.get("metadata", {})
                    )
                    results.append(SearchResult(
                        memory=memory,
                        score=item.get("score", item.get("similarity", 0.0)),
                        snippet=item.get("snippet", memory.content[:200])
                    ))

                return results
            else:
                print(f"Search failed: {response.status_code} - {response.text[:200]}")
                return []

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def add_document(
        self,
        url: str = None,
        file_path: str = None,
        content: str = None,
        user_id: str = "default"
    ) -> Optional[str]:
        """
        Add a document (URL, file, or raw content) to memory.

        Args:
            url: URL to fetch and store
            file_path: Path to local file
            content: Raw content (for text documents)
            user_id: User identifier

        Returns:
            Document ID if successful
        """
        if not self.configured:
            return None

        payload = {}

        if url:
            payload["url"] = url
        elif file_path:
            path = Path(file_path)
            if path.exists():
                payload["content"] = path.read_text()
                payload["metadata"] = {"filename": path.name}
        elif content:
            payload["content"] = content
        else:
            return None

        try:
            response = self.client.post(
                f"{self.base_url}/documents",
                json=payload,
                params={"userId": user_id}
            )

            if response.status_code in (200, 201):
                data = response.json()
                return data.get("id") or data.get("documentId")
            else:
                print(f"Add document failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"Add document error: {e}")
            return None

    def sync_from_events(
        self,
        events_path: str = "memory/events.jsonl",
        user_id: str = "default"
    ) -> int:
        """
        Sync local events.jsonl to Supermemory.

        Returns count of synced entries.
        """
        if not self.configured:
            return 0

        events_file = Path(events_path)
        if not events_file.exists():
            print(f"Events file not found: {events_path}")
            return 0

        count = 0

        with open(events_file) as f:
            for line in f:
                try:
                    event = json.loads(line)

                    # Convert event to memory
                    kind = event.get("kind", "unknown")
                    data = event.get("data", {})

                    if kind == "workflow":
                        content = f"Workflow: {data.get('intent', 'Unknown')}\n"
                        content += f"Steps: {json.dumps(data.get('steps', []))}\n"
                        content += f"Result: {data.get('result', 'Unknown')}"
                        tags = ["workflow", "trapdoor"]
                    elif kind == "chat":
                        content = data.get("content", str(data))
                        tags = ["chat", "trapdoor"]
                    elif kind == "lesson":
                        content = data.get("lesson", str(data))
                        tags = ["lesson", "trapdoor"]
                    else:
                        content = json.dumps(data)
                        tags = [kind, "trapdoor"]

                    memory_id = self.add_memory(
                        content=content,
                        source="trapdoor_sync",
                        tags=tags,
                        metadata={"original_kind": kind, "synced_at": datetime.now().isoformat()},
                        user_id=user_id
                    )

                    if memory_id:
                        count += 1

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Sync error: {e}")
                    continue

        return count

    def health(self) -> Dict[str, Any]:
        """Check API health and configuration."""
        status = {
            "configured": self.configured,
            "api_url": self.base_url,
            "api_key_set": bool(self.api_key),
            "api_key_preview": f"{self.api_key[:10]}..." if self.api_key else None
        }

        if self.configured:
            try:
                # Try a simple search to verify connectivity
                response = self.client.get(f"{self.base_url}/health")
                status["api_status"] = "connected" if response.status_code == 200 else f"error: {response.status_code}"
            except Exception as e:
                status["api_status"] = f"error: {e}"

        return status

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


# ==============================================================================
# FastAPI Endpoints
# ==============================================================================

def create_supermemory_router():
    """
    Create FastAPI router for Supermemory endpoints.

    Add to your FastAPI app:
        from supermemory_bridge import create_supermemory_router
        app.include_router(create_supermemory_router(), prefix="/v1/supermemory")
    """
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter()
    bridge = SupermemoryBridge()

    class AddRequest(BaseModel):
        content: str
        source: str = "api"
        tags: List[str] = []
        metadata: Dict[str, Any] = {}

    class SearchRequest(BaseModel):
        query: str
        limit: int = 10
        filters: Dict[str, Any] = {}

    class DocumentRequest(BaseModel):
        url: Optional[str] = None
        content: Optional[str] = None
        file_path: Optional[str] = None

    @router.get("/health")
    def supermemory_health():
        return bridge.health()

    @router.post("/add")
    def supermemory_add(req: AddRequest):
        memory_id = bridge.add_memory(
            content=req.content,
            source=req.source,
            tags=req.tags,
            metadata=req.metadata
        )
        if memory_id:
            return {"status": "added", "id": memory_id}
        raise HTTPException(500, "Failed to add memory")

    @router.post("/search")
    def supermemory_search(req: SearchRequest):
        results = bridge.search(
            query=req.query,
            limit=req.limit,
            filters=req.filters
        )
        return {
            "query": req.query,
            "results": [r.to_dict() for r in results],
            "count": len(results)
        }

    @router.post("/document")
    def supermemory_document(req: DocumentRequest):
        doc_id = bridge.add_document(
            url=req.url,
            content=req.content,
            file_path=req.file_path
        )
        if doc_id:
            return {"status": "added", "id": doc_id}
        raise HTTPException(500, "Failed to add document")

    @router.post("/sync")
    def supermemory_sync():
        count = bridge.sync_from_events()
        return {"status": "synced", "entries": count}

    return router


# ==============================================================================
# CLI
# ==============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Supermemory Bridge")
    subparsers = parser.add_subparsers(dest="command")

    # Configure
    config_parser = subparsers.add_parser("configure", help="Set API key")
    config_parser.add_argument("api_key", help="Supermemory API key")

    # Health
    subparsers.add_parser("health", help="Check status")

    # Add
    add_parser = subparsers.add_parser("add", help="Add a memory")
    add_parser.add_argument("content", help="Content to store")
    add_parser.add_argument("--source", default="cli")
    add_parser.add_argument("--tags", nargs="+", default=[])

    # Search
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=5)

    # Document
    doc_parser = subparsers.add_parser("document", help="Add document")
    doc_parser.add_argument("--url", help="URL to fetch")
    doc_parser.add_argument("--file", help="File path")
    doc_parser.add_argument("--content", help="Raw content")

    # Sync
    sync_parser = subparsers.add_parser("sync", help="Sync from events.jsonl")
    sync_parser.add_argument("--path", default="memory/events.jsonl")

    args = parser.parse_args()
    bridge = SupermemoryBridge()

    if args.command == "configure":
        save_config({"api_key": args.api_key})
        print(f"✓ API key saved to {CONFIG_FILE}")

    elif args.command == "health":
        print(json.dumps(bridge.health(), indent=2))

    elif args.command == "add":
        memory_id = bridge.add_memory(
            content=args.content,
            source=args.source,
            tags=args.tags
        )
        print(f"Added: {memory_id}" if memory_id else "Failed")

    elif args.command == "search":
        results = bridge.search(args.query, limit=args.limit)
        for i, r in enumerate(results, 1):
            print(f"\n--- {i}. (score: {r.score:.3f}) ---")
            print(f"Source: {r.memory.source}")
            print(f"Content: {r.snippet[:200]}...")

    elif args.command == "document":
        doc_id = bridge.add_document(
            url=args.url,
            file_path=args.file,
            content=args.content
        )
        print(f"Added document: {doc_id}" if doc_id else "Failed")

    elif args.command == "sync":
        count = bridge.sync_from_events(args.path)
        print(f"Synced {count} entries")

    else:
        parser.print_help()

    bridge.close()


if __name__ == "__main__":
    main()
