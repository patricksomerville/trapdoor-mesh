#!/usr/bin/env python3
"""
Memory Bridge - Qdrant/Cipher integration for Trapdoor Mesh

This module provides shared memory capabilities across the mesh network:
- Store knowledge, code patterns, reasoning traces
- Semantic search across all stored memories
- Cross-application memory sharing (Claude Desktop, VS Code, Cursor, Claude Code)

Requires Qdrant running at localhost:6333 (Docker container)
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

# Try to import qdrant, fall back gracefully
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

# Try to import embedding providers
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# ==============================================================================
# Configuration
# ==============================================================================

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
EMBEDDING_DIM = 1536  # OpenAI ada-002 dimension
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Collection names (matching Cipher setup)
COLLECTIONS = {
    "knowledge": "trapdoor_knowledge",      # Code patterns, business logic
    "reasoning": "trapdoor_reasoning",      # Reasoning traces, problem-solving
    "workflows": "trapdoor_workflows",      # Workflow patterns from memory/events.jsonl
}


# ==============================================================================
# Data Models
# ==============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    category: str  # knowledge, reasoning, workflow
    source: str    # machine name or application
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: str
    vector: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SearchResult:
    """A search result with similarity score."""
    entry: MemoryEntry
    score: float

    def to_dict(self) -> Dict:
        return {
            "entry": self.entry.to_dict(),
            "score": self.score
        }


# ==============================================================================
# Embedding Generation
# ==============================================================================

def get_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using available providers.

    Priority:
    1. OpenAI API (if OPENAI_API_KEY set)
    2. Local Ollama (if running)
    3. None (fall back to keyword search)
    """
    # Try OpenAI
    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        try:
            client = openai.OpenAI()
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text[:8000]  # Truncate to model limit
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI embedding failed: {e}")

    # Try Ollama
    if HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{OLLAMA_HOST}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text[:8000]}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embedding = data.get("embedding", [])
                    # Pad or truncate to EMBEDDING_DIM
                    if len(embedding) < EMBEDDING_DIM:
                        embedding.extend([0.0] * (EMBEDDING_DIM - len(embedding)))
                    return embedding[:EMBEDDING_DIM]
        except Exception as e:
            print(f"Ollama embedding failed: {e}")

    return None


def content_hash(content: str) -> str:
    """Generate a unique ID from content."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# ==============================================================================
# Memory Bridge Class
# ==============================================================================

class MemoryBridge:
    """
    Bridge between Trapdoor mesh and Qdrant vector database.

    Provides:
    - Store: Add memories to shared knowledge base
    - Search: Semantic search across all memories
    - Sync: Import from local memory/events.jsonl
    """

    def __init__(self, host: str = QDRANT_HOST, port: int = QDRANT_PORT):
        self.host = host
        self.port = port
        self.client = None
        self._connected = False

        if QDRANT_AVAILABLE:
            try:
                self.client = QdrantClient(host=host, port=port)
                self._connected = True
                self._ensure_collections()
            except Exception as e:
                print(f"Failed to connect to Qdrant: {e}")
                self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def _ensure_collections(self):
        """Create collections if they don't exist."""
        if not self.client:
            return

        existing = {c.name for c in self.client.get_collections().collections}

        for key, name in COLLECTIONS.items():
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIM,
                        distance=Distance.COSINE
                    )
                )
                print(f"Created collection: {name}")

    def store(
        self,
        content: str,
        category: str = "knowledge",
        source: str = "unknown",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store a memory entry.

        Args:
            content: The text content to store
            category: knowledge, reasoning, or workflow
            source: Origin (machine name, app name)
            tags: Optional tags for filtering
            metadata: Optional additional metadata

        Returns:
            Entry ID if successful, None otherwise
        """
        if not self._connected:
            return None

        # Generate embedding
        vector = get_embedding(content)
        if not vector:
            print("Warning: No embedding generated, memory may not be searchable")
            vector = [0.0] * EMBEDDING_DIM

        # Create entry
        entry_id = content_hash(content)
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            category=category,
            source=source,
            tags=tags or [],
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
            vector=vector
        )

        # Store in appropriate collection
        collection = COLLECTIONS.get(category, COLLECTIONS["knowledge"])

        try:
            self.client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(
                        id=entry_id,
                        vector=vector,
                        payload={
                            "content": content,
                            "category": category,
                            "source": source,
                            "tags": tags or [],
                            "metadata": metadata or {},
                            "created_at": entry.created_at
                        }
                    )
                ]
            )
            return entry_id
        except Exception as e:
            print(f"Failed to store memory: {e}")
            return None

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Semantic search across memories.

        Args:
            query: Natural language search query
            category: Filter by category (knowledge, reasoning, workflow)
            source: Filter by source machine/app
            tags: Filter by tags
            limit: Max results to return

        Returns:
            List of SearchResult objects
        """
        if not self._connected:
            return []

        # Generate query embedding
        query_vector = get_embedding(query)
        if not query_vector:
            print("Warning: Could not generate query embedding")
            return []

        # Build filter
        filter_conditions = []
        if source:
            filter_conditions.append(
                FieldCondition(key="source", match=MatchValue(value=source))
            )
        if tags:
            for tag in tags:
                filter_conditions.append(
                    FieldCondition(key="tags", match=MatchValue(value=tag))
                )

        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Search in appropriate collection(s)
        collections_to_search = (
            [COLLECTIONS[category]] if category and category in COLLECTIONS
            else list(COLLECTIONS.values())
        )

        results = []
        for collection in collections_to_search:
            try:
                hits = self.client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    query_filter=search_filter,
                    limit=limit
                )

                for hit in hits:
                    payload = hit.payload
                    entry = MemoryEntry(
                        id=str(hit.id),
                        content=payload.get("content", ""),
                        category=payload.get("category", "unknown"),
                        source=payload.get("source", "unknown"),
                        tags=payload.get("tags", []),
                        metadata=payload.get("metadata", {}),
                        created_at=payload.get("created_at", "")
                    )
                    results.append(SearchResult(entry=entry, score=hit.score))
            except Exception as e:
                print(f"Search failed in {collection}: {e}")

        # Sort by score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def sync_from_events(self, events_path: str = "memory/events.jsonl") -> int:
        """
        Import workflows from local events.jsonl into Qdrant.

        Returns number of entries imported.
        """
        if not self._connected:
            return 0

        try:
            from pathlib import Path
            events_file = Path(events_path)
            if not events_file.exists():
                print(f"Events file not found: {events_path}")
                return 0

            count = 0
            with open(events_file) as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get("kind") == "workflow":
                            data = event.get("data", {})
                            content = f"Workflow: {data.get('intent', 'Unknown')}\n"
                            content += f"Steps: {json.dumps(data.get('steps', []))}\n"
                            content += f"Result: {data.get('result', 'Unknown')}"

                            self.store(
                                content=content,
                                category="workflow",
                                source="local",
                                tags=["imported", "workflow"],
                                metadata=data
                            )
                            count += 1
                    except json.JSONDecodeError:
                        continue

            return count
        except Exception as e:
            print(f"Sync failed: {e}")
            return 0

    def health(self) -> Dict[str, Any]:
        """Return health status and stats."""
        if not self._connected:
            return {
                "status": "disconnected",
                "qdrant_available": QDRANT_AVAILABLE,
                "host": self.host,
                "port": self.port
            }

        try:
            collections_info = {}
            for key, name in COLLECTIONS.items():
                try:
                    info = self.client.get_collection(name)
                    collections_info[key] = {
                        "name": name,
                        "points_count": info.points_count,
                        "vectors_count": info.vectors_count
                    }
                except:
                    collections_info[key] = {"name": name, "status": "not found"}

            return {
                "status": "connected",
                "host": self.host,
                "port": self.port,
                "collections": collections_info,
                "embedding_available": get_embedding("test") is not None
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# ==============================================================================
# FastAPI Endpoints (for integration with trapdoor server)
# ==============================================================================

def create_memory_router():
    """
    Create FastAPI router for memory endpoints.

    Add to your FastAPI app:
        from memory_bridge import create_memory_router
        app.include_router(create_memory_router(), prefix="/v1/memory")
    """
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter()
    bridge = MemoryBridge()

    class StoreRequest(BaseModel):
        content: str
        category: str = "knowledge"
        source: str = "api"
        tags: List[str] = []
        metadata: Dict[str, Any] = {}

    class SearchRequest(BaseModel):
        query: str
        category: Optional[str] = None
        source: Optional[str] = None
        tags: Optional[List[str]] = None
        limit: int = 10

    @router.get("/health")
    def memory_health():
        return bridge.health()

    @router.post("/store")
    def memory_store(req: StoreRequest):
        entry_id = bridge.store(
            content=req.content,
            category=req.category,
            source=req.source,
            tags=req.tags,
            metadata=req.metadata
        )
        if entry_id:
            return {"status": "stored", "id": entry_id}
        raise HTTPException(500, "Failed to store memory")

    @router.post("/search")
    def memory_search(req: SearchRequest):
        results = bridge.search(
            query=req.query,
            category=req.category,
            source=req.source,
            tags=req.tags,
            limit=req.limit
        )
        return {
            "query": req.query,
            "results": [r.to_dict() for r in results],
            "count": len(results)
        }

    @router.post("/sync")
    def memory_sync():
        count = bridge.sync_from_events()
        return {"status": "synced", "entries_imported": count}

    return router


# ==============================================================================
# CLI
# ==============================================================================

def main():
    """CLI for testing memory bridge."""
    import argparse

    parser = argparse.ArgumentParser(description="Memory Bridge CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Health check
    subparsers.add_parser("health", help="Check connection status")

    # Store
    store_parser = subparsers.add_parser("store", help="Store a memory")
    store_parser.add_argument("content", help="Content to store")
    store_parser.add_argument("--category", default="knowledge")
    store_parser.add_argument("--source", default="cli")
    store_parser.add_argument("--tags", nargs="+", default=[])

    # Search
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--category", default=None)
    search_parser.add_argument("--limit", type=int, default=5)

    # Sync
    subparsers.add_parser("sync", help="Sync from events.jsonl")

    args = parser.parse_args()
    bridge = MemoryBridge()

    if args.command == "health":
        print(json.dumps(bridge.health(), indent=2))

    elif args.command == "store":
        entry_id = bridge.store(
            content=args.content,
            category=args.category,
            source=args.source,
            tags=args.tags
        )
        print(f"Stored with ID: {entry_id}" if entry_id else "Failed to store")

    elif args.command == "search":
        results = bridge.search(args.query, category=args.category, limit=args.limit)
        for i, r in enumerate(results, 1):
            print(f"\n--- Result {i} (score: {r.score:.3f}) ---")
            print(f"Source: {r.entry.source}")
            print(f"Content: {r.entry.content[:200]}...")

    elif args.command == "sync":
        count = bridge.sync_from_events()
        print(f"Synced {count} entries")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
