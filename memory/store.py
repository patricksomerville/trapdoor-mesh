from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
import heapq
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


MEMORY_DIR = Path(os.getenv("TRAPDOOR_MEMORY_DIR", Path(__file__).resolve().parent))
EVENTS_PATH = MEMORY_DIR / "events.jsonl"
LESSONS_PATH = MEMORY_DIR / "lessons.jsonl"


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _append(path: Path, record: Dict[str, Any]) -> None:
    _ensure_dir()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_event(kind: str, data: Dict[str, Any]) -> None:
    event = {
        "ts": time.time(),
        "kind": kind,
        "data": data,
    }
    _append(EVENTS_PATH, event)


def add_lesson(title: str, summary: str, *, tags: Optional[List[str]] = None) -> None:
    lesson = {
        "ts": time.time(),
        "title": title.strip(),
        "summary": summary.strip(),
        "tags": tags or [],
    }
    _append(LESSONS_PATH, lesson)


def _load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def get_recent_events(limit: int = 10) -> List[Dict[str, Any]]:
    events = list(_load_jsonl(EVENTS_PATH))
    return events[-limit:]


def get_recent_lessons(limit: int = 10) -> List[Dict[str, Any]]:
    lessons = list(_load_jsonl(LESSONS_PATH))
    return lessons[-limit:]


def search_events(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches: List[Dict[str, Any]] = []
    for event in _load_jsonl(EVENTS_PATH):
        payload = json.dumps(event, ensure_ascii=False)
        if pattern.search(payload):
            matches.append(event)
            if len(matches) >= limit:
                break
    return matches


def search_lessons(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches: List[Dict[str, Any]] = []
    for lesson in _load_jsonl(LESSONS_PATH):
        payload = json.dumps(lesson, ensure_ascii=False)
        if pattern.search(payload):
            matches.append(lesson)
            if len(matches) >= limit:
                break
    return matches


def describe_recent_activity(limit: int = 20) -> Dict[str, Any]:
    events = get_recent_events(limit)
    lessons = get_recent_lessons(limit)
    stats = {"total_events": len(events), "kinds": {}}
    for event in events:
        stats["kinds"][event.get("kind")] = stats["kinds"].get(event.get("kind"), 0) + 1
    return {"events": events, "lessons": lessons, "stats": stats}


def _keyword_set(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9_]+", text.lower())
    return {tok for tok in tokens if len(tok) > 2}


def get_relevant_lessons(query: str, *, tags: Optional[Sequence[str]] = None, limit: int = 3) -> List[Dict[str, Any]]:
    lessons = list(_load_jsonl(LESSONS_PATH))
    if not lessons:
        return []
    query_keys = _keyword_set(query)
    if tags:
        query_keys.update(t.lower() for t in tags if t)

    scored: List[Tuple[int, float, Dict[str, Any]]] = []
    for lesson in lessons:
        lesson_text = f"{lesson.get('title','')} {lesson.get('summary','')} {' '.join(lesson.get('tags') or [])}"
        lesson_keys = _keyword_set(lesson_text)
        score = len(query_keys & lesson_keys)
        if tags and set(lesson.get("tags") or []) & set(tags):
            score += 2
        if score == 0 and query_keys:
            continue
        scored.append((score, lesson.get("ts", 0.0), lesson))

    if not scored:
        # fall back to most recent lessons
        return lessons[-limit:]

    top = heapq.nlargest(limit, scored, key=lambda item: (item[0], item[1]))
    return [item[2] for item in top]


def format_lessons_as_bullets(lessons: Sequence[Dict[str, Any]]) -> str:
    bullets: List[str] = []
    for lesson in lessons:
        title = lesson.get("title") or "Lesson"
        summary = lesson.get("summary") or ""
        tags = lesson.get("tags") or []
        tag_str = f" (tags: {', '.join(tags)})" if tags else ""
        bullets.append(f"- {title}{tag_str}: {summary}")
    return "\n".join(bullets)


def add_auto_lesson(prompt: str, response: str, *, tags: Optional[List[str]] = None) -> None:
    snippet_prompt = prompt.strip().replace("\n", " ")
    snippet_response = response.strip().replace("\n", " ")
    summary = f"User asked: {snippet_prompt[:200]} | Response: {snippet_response[:200]}"
    title = f"Auto lesson {time.strftime('%Y-%m-%d %H:%M:%S')}"
    add_lesson(title, summary, tags=tags or ["auto"])


# ============================================================
# WORKFLOW TRACKING (Added for learning from interactions)
# ============================================================

def record_workflow_event(
    intent: str,
    steps: List[Dict[str, Any]],
    result: str,
    success: bool,
    duration: float,
    *,
    tags: Optional[List[str]] = None
) -> None:
    """Record a complete workflow execution"""
    workflow = {
        "ts": time.time(),
        "intent": intent.strip()[:500],  # User's original request
        "steps": steps,  # All commands executed
        "result": result.strip()[:500],  # Final outcome
        "success": success,
        "duration": duration,
        "step_count": len(steps),
        "tags": tags or _extract_workflow_tags(intent, steps)
    }
    _append(EVENTS_PATH, {"kind": "workflow", "data": workflow})


def _extract_workflow_tags(intent: str, steps: List[Dict]) -> List[str]:
    """Auto-tag workflows based on content"""
    tags = []
    intent_lower = intent.lower()
    steps_str = str(steps).lower()

    # Detect patterns in steps
    if "git" in steps_str:
        tags.append("git")
    if "npm" in steps_str or "package.json" in steps_str:
        tags.append("nodejs")
    if "test" in steps_str:
        tags.append("testing")
    if "python" in steps_str or ".py" in steps_str:
        tags.append("python")
    if "docker" in steps_str:
        tags.append("docker")

    # Detect patterns in intent
    if any(word in intent_lower for word in ["deploy", "release", "publish"]):
        tags.append("deployment")
    if any(word in intent_lower for word in ["check", "status", "verify"]):
        tags.append("status_check")

    return tags


def find_similar_workflows(intent: str, limit: int = 5, min_success_rate: float = 0.5) -> List[Dict]:
    """Find workflows similar to current intent"""
    workflows = [
        e["data"] for e in _load_jsonl(EVENTS_PATH)
        if e.get("kind") == "workflow"
    ]

    if not workflows:
        return []

    # Score by intent similarity and success
    scored = []
    intent_tokens = set(intent.lower().split())

    for wf in workflows:
        wf_tokens = set(wf["intent"].lower().split())
        if not intent_tokens or not wf_tokens:
            continue

        similarity = len(intent_tokens & wf_tokens) / len(intent_tokens | wf_tokens)

        # Boost successful workflows
        score = similarity * (1.5 if wf["success"] else 0.5)

        scored.append((score, wf))

    # Sort and filter
    scored.sort(reverse=True, key=lambda x: x[0])
    return [wf for score, wf in scored[:limit] if score > 0.1]


def get_workflow_stats(intent: str = None) -> Dict[str, Any]:
    """Get statistics about workflow executions"""
    workflows = [
        e["data"] for e in _load_jsonl(EVENTS_PATH)
        if e.get("kind") == "workflow"
    ]

    if not workflows:
        return {"total": 0, "successful": 0, "failed": 0, "avg_duration": 0}

    # Filter by intent if provided
    if intent:
        intent_lower = intent.lower()
        workflows = [w for w in workflows if intent_lower in w["intent"].lower()]

    total = len(workflows)
    successful = sum(1 for w in workflows if w["success"])
    failed = total - successful
    durations = [w["duration"] for w in workflows if w.get("duration")]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": successful / total if total > 0 else 0,
        "avg_duration": avg_duration
    }


def format_workflow_suggestions(workflows: List[Dict]) -> str:
    """Format past successful workflows as suggestions"""
    if not workflows:
        return ""

    suggestions = ["Based on similar past requests, you previously:"]

    for wf in workflows[:3]:  # Top 3 suggestions
        steps_summary = " → ".join([
            f"{step.get('operation', 'unknown')}({step.get('path', step.get('cmd', [''])[0] if isinstance(step.get('cmd'), list) else '')})"
            for step in wf.get("steps", [])[:5]  # First 5 steps
        ])

        status = "✓ succeeded" if wf.get("success") else "✗ failed"
        duration = wf.get("duration", 0)

        suggestions.append(
            f"\n- For '{wf['intent'][:60]}...': {steps_summary}"
            f"\n  ({status}, took {duration:.1f}s)"
        )

    suggestions.append("\n\nConsider following a similar workflow if appropriate.")
    return "\n".join(suggestions)
