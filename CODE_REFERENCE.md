# Trapdoor Code Reference Guide
## Detailed Implementation References for Security Features

---

## Authentication & Authorization

### Token Definition & Loading
**File:** `/Users/patricksomerville/Desktop/local_agent_server.py`  
**Lines:** 672-690

```python
AUTH_TOKEN = os.getenv("AUTH_TOKEN")  # backward-compat single-token env
AUTH_TOKEN_FILE = os.getenv("AUTH_TOKEN_FILE")

AUTH_TOKENS: Set[str] = set()
if AUTH_TOKEN:
    for t in AUTH_TOKEN.split(","):
        t = t.strip()
        if t:
            AUTH_TOKENS.add(t)

if AUTH_TOKEN_FILE and os.path.exists(AUTH_TOKEN_FILE):
    try:
        with open(AUTH_TOKEN_FILE, "r", encoding="utf-8") as f:
            for line in f:
                tok = line.strip()
                if tok:
                    AUTH_TOKENS.add(tok)
    except Exception:
        pass
```

### Token Validation Function
**Lines:** 845-856

```python
def _require_auth(authorization: Optional[str]) -> Optional[str]:
    if AUTH_TOKENS:  # Only enforce if at least one token is configured
        if not authorization or not authorization.startswith("Bearer "):
            _log_event("auth_failure", reason="missing_header")
            raise HTTPException(status_code=401, 
                               detail="Missing/invalid Authorization header")
        token = authorization.split(" ", 1)[1]
        if token not in AUTH_TOKENS:
            _log_event("auth_failure", reason="invalid_token")
            raise HTTPException(status_code=403, detail="Invalid token")
        return _enforce_rate_limit(token)
    return None
```

### Token Fingerprinting (for Rate Limiting)
**Lines:** 794-795

```python
def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
```

---

## Filesystem Operations

### Path Resolution & Validation
**Lines:** 858-866

```python
def _resolve_path(p: str) -> Path:
    path = Path(p).expanduser()
    
    if not ALLOW_ABSOLUTE and not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    else:
        path = path.resolve()
    
    if not ALLOW_ABSOLUTE and BASE_DIR not in path.parents and path != BASE_DIR:
        raise HTTPException(status_code=403, 
                           detail="Path outside BASE_DIR not allowed")
    return path
```

### /fs/ls Endpoint
**Lines:** 924-968

```python
@app.get("/fs/ls")
def fs_ls(path: Optional[str] = None, 
          authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    tgt = _resolve_path(path or str(BASE_DIR))
    
    if not tgt.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    
    if tgt.is_file():
        stat = tgt.stat()
        data = {
            "path": str(tgt),
            "type": "file",
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
        }
    else:
        entries = []
        for entry in sorted(tgt.iterdir()):
            try:
                st = entry.stat()
                entries.append({
                    "name": entry.name,
                    "path": str(entry),
                    "type": "dir" if entry.is_dir() else "file",
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                })
            except Exception:
                continue
        data = {"path": str(tgt), "entries": entries}
    
    _log_event(
        "fs_ls",
        token=token_fp,
        path=str(tgt),
        status="ok",
        entries=len(data.get("entries", [])),
    )
    
    return data
```

### /fs/read Endpoint (Text & Binary)
**Lines:** 971-1004

```python
@app.get("/fs/read")
def fs_read(path: str, authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    tgt = _resolve_path(path)
    
    if not tgt.exists() or not tgt.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        text = tgt.read_text(encoding="utf-8")
        data = {"path": str(tgt), "content": text}
        _log_event("fs_read", token=token_fp, path=str(tgt), 
                  status="ok", mode="text", length=len(text))
        return data
    except UnicodeDecodeError:
        # Binary file - return size only
        data = tgt.read_bytes()
        result = {"path": str(tgt), "bytes": len(data)}
        _log_event("fs_read", token=token_fp, path=str(tgt), 
                  status="ok", mode="binary", length=len(data))
        return result
```

### /fs/write Endpoint
**Lines:** 1007-1027

```python
@app.post("/fs/write")
def fs_write(body: FSWriteBody, authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    tgt = _resolve_path(body.path)
    tgt.parent.mkdir(parents=True, exist_ok=True)
    
    mode = "a" if body.mode == "append" else "w"
    content = body.content or ""
    
    with open(tgt, mode, encoding="utf-8") as f:
        f.write(content)
    
    written_len = len(content)
    _log_event("fs_write", token=token_fp, path=str(tgt), 
              status="ok", mode=body.mode or "write", written=written_len)
    
    return {"written": written_len, "path": str(tgt)}
```

### /fs/mkdir Endpoint
**Lines:** 1030-1044

```python
@app.post("/fs/mkdir")
def fs_mkdir(body: FSMkdirBody, authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    tgt = _resolve_path(body.path)
    tgt.mkdir(parents=bool(body.parents), exist_ok=bool(body.exist_ok))
    
    _log_event("fs_mkdir", token=token_fp, path=str(tgt), 
              status="ok", parents=bool(body.parents))
    
    return {"path": str(tgt), "created": True}
```

### /fs/rm Endpoint
**Lines:** 1047-1079

```python
@app.post("/fs/rm")
def fs_rm(body: FSRmBody, authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    tgt = _resolve_path(body.path)
    
    if not tgt.exists():
        _log_event("fs_rm", token=token_fp, path=str(tgt), status="missing")
        return {"path": str(tgt), "removed": False}
    
    if tgt.is_dir():
        if body.recursive:
            shutil.rmtree(tgt)
        else:
            tgt.rmdir()
    else:
        tgt.unlink()
    
    _log_event("fs_rm", token=token_fp, path=str(tgt), 
              status="ok", recursive=bool(body.recursive))
    
    return {"path": str(tgt), "removed": True}
```

---

## Command Execution

### /exec Endpoint
**Lines:** 1082-1139

```python
@app.post("/exec")
def exec_cmd(body: ExecBody, authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    cmd = list(body.cmd)
    
    if body.sudo:
        if not ALLOW_SUDO:
            raise HTTPException(status_code=403, 
                              detail="Sudo not allowed (set ALLOW_SUDO=1)")
        cmd = ["sudo"] + cmd
    
    cwd = _resolve_path(body.cwd) if body.cwd else BASE_DIR
    cmd_preview = " ".join(cmd[:4])
    
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=body.timeout or 300,
            text=True,
        )
    except subprocess.TimeoutExpired:
        _log_event(
            "exec",
            token=token_fp,
            status="timeout",
            cmd=cmd,
            cwd=str(cwd),
            timeout=body.timeout or 300,
        )
        raise HTTPException(status_code=504, detail="Command timed out")
    
    rc = completed.returncode
    _log_event(
        "exec",
        token=token_fp,
        status="ok",
        cmd=cmd,
        cwd=str(cwd),
        rc=rc,
    )
    
    return {"cmd": cmd, "cwd": str(cwd), "rc": rc, 
            "stdout": completed.stdout, "stderr": completed.stderr}
```

**ExecBody Model:**
```python
class ExecBody(BaseModel):
    cmd: List[str]
    cwd: Optional[str] = None
    timeout: Optional[int] = 300
    sudo: Optional[bool] = False
```

---

## Rate Limiting

### Rate Limit Enforcement
**Lines:** 812-842

```python
def _enforce_rate_limit(token: Optional[str] = None, 
                       fingerprint: Optional[str] = None) -> str:
    if fingerprint is None:
        if token is None:
            raise ValueError("token or fingerprint required for rate limiting")
        fingerprint = _token_fingerprint(token)
    
    # Check if rate limiting is disabled
    if FS_EXEC_MAX_REQUESTS_PER_MINUTE <= 0 or FS_EXEC_WINDOW_SECONDS <= 0:
        return fingerprint
    
    now = time.time()
    cutoff = now - FS_EXEC_WINDOW_SECONDS
    
    with _RATE_LIMIT_LOCK:
        history = _RATE_LIMIT_HISTORY.setdefault(fingerprint, deque())
        
        # Remove old entries outside the window
        while history and history[0] < cutoff:
            history.popleft()
        
        # Check if limit exceeded
        if len(history) >= FS_EXEC_MAX_REQUESTS_PER_MINUTE:
            _log_event(
                "rate_limit_block",
                token=fingerprint,
                count=len(history),
                window=FS_EXEC_WINDOW_SECONDS,
            )
            raise HTTPException(status_code=429, 
                              detail="Too many tool requests, slow down")
        
        # Record this request
        history.append(now)
    
    return fingerprint
```

### Rate Limit Globals
**Lines:** 706-709

```python
FS_EXEC_MAX_REQUESTS_PER_MINUTE = int(os.getenv("FS_EXEC_MAX_REQUESTS_PER_MINUTE", "120"))
FS_EXEC_WINDOW_SECONDS = int(os.getenv("FS_EXEC_WINDOW_SECONDS", "60"))
_RATE_LIMIT_HISTORY: Dict[str, deque] = {}
_RATE_LIMIT_LOCK = threading.Lock()
```

---

## Audit Logging

### Event Logging Function
**Lines:** 798-809

```python
def _log_event(event: str, **payload: Any) -> None:
    if OBS_LOG_PATH is None:
        return
    
    entry = {"ts": time.time(), "event": event, "backend": BACKEND}
    for key, value in payload.items():
        if value is not None:
            entry[key] = value
    
    try:
        with OBS_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
```

### Logging Path Configuration
**Lines:** 695-704

```python
_obs_log_path_env = os.getenv("OBS_LOG_PATH")
if _obs_log_path_env == "":
    OBS_LOG_PATH: Optional[Path] = None
else:
    default_obs_path = Path(os.getenv("OBS_LOG_PATH", 
                           str(Path(".proxy_runtime") / "audit.log")))
    OBS_LOG_PATH = default_obs_path
    try:
        OBS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        OBS_LOG_PATH = None
```

---

## Memory & Learning System

### Lesson Context Building
**File:** `/Users/patricksomerville/Desktop/local_agent_server.py`  
**Lines:** 752-769

```python
def _build_lesson_context(user_messages: List[Dict[str, Any]], 
                         tags: Optional[List[str]] = None) -> Optional[str]:
    if not (MEMORY_ENABLED and memory_store is not None):
        return None
    
    query_text = _user_text_from_messages(user_messages)
    
    if not query_text.strip():
        return None
    
    try:
        lessons = memory_store.get_relevant_lessons(
            query_text, 
            tags=tags, 
            limit=MEMORY_LESSON_LIMIT
        )
    except Exception:
        return None
    
    if not lessons:
        return None
    
    try:
        body = memory_store.format_lessons_as_bullets(lessons)
    except Exception:
        return None
    
    if not body:
        return None
    
    return body
```

### Memory Event Recording
**Lines:** 733-739

```python
def _memory_record(kind: str, data: Dict[str, Any]) -> None:
    if memory_store is None:
        return
    
    try:
        memory_store.record_event(kind, data)
    except Exception:
        pass
```

### Auto-Lesson Generation
**Lines:** 776-791

```python
def _auto_reflect(user_messages: List[Dict[str, Any]], 
                 response_text: str, 
                 tags: Optional[List[str]] = None) -> None:
    if not (MEMORY_ENABLED and memory_store is not None):
        return
    
    try:
        memory_store.add_auto_lesson(
            _user_text_from_messages(user_messages),
            response_text,
            tags=tags or [],
        )
    except Exception:
        pass
```

### Lesson Injection into Chat
**Lines:** 257-258 (in chat endpoint)

```python
lesson_context = _build_lesson_context(user_messages, tags=["chat"])
msgs = _insert_context_message(msgs, lesson_context)
```

### Memory Implementation
**File:** `/Users/patricksomerville/Desktop/Trapdoor/memory/store.py`  
**Lines:** 108-132

```python
def get_relevant_lessons(query: str, *, 
                        tags: Optional[Sequence[str]] = None, 
                        limit: int = 3) -> List[Dict[str, Any]]:
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
        return lessons[-limit:]
    
    top = heapq.nlargest(limit, scored, key=lambda item: (item[0], item[1]))
    return [item[2] for item in top]
```

---

## Batch Operations

### /batch Endpoint
**Lines:** 1142-1278

Key implementation:
```python
@app.post("/batch")
def batch(req: BatchRequest, authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    results: List[Dict[str, Any]] = []
    first_item = True
    op_counts: Dict[str, int] = {}
    
    for item in req.items:
        try:
            if token_fp:
                if first_item:
                    first_item = False
                else:
                    _enforce_rate_limit(fingerprint=token_fp)  # Rate limit all but first
            
            op_counts[item.op] = op_counts.get(item.op, 0) + 1
            
            # Execute operation (fs_ls, fs_read, fs_write, fs_mkdir, fs_rm, exec)
            if item.op == "fs_ls":
                # ... ls operation ...
            elif item.op == "fs_read":
                # ... read operation ...
            # ... etc ...
            
            results.append({"ok": True, "op": item.op, "data": data})
        
        except HTTPException as he:
            results.append({"ok": False, "op": item.op, 
                          "error": {"status": he.status_code, "detail": he.detail}})
            if not req.continue_on_error:
                break
        
        except Exception as e:
            results.append({"ok": False, "op": item.op, 
                          "error": {"status": 500, "detail": str(e)}})
            if not req.continue_on_error:
                break
    
    # Log batch results
    _log_event(
        "batch",
        token=token_fp,
        status="ok" if all(r.get("ok") for r in results) else "partial",
        total=len(results),
        successes=sum(1 for r in results if r.get("ok")),
        failures=sum(1 for r in results if not r.get("ok")),
    )
    
    return {"items": results, "total": len(results), ...}
```

---

## Configuration & Initialization

### Environment Variables
**Lines:** 60-65, 672-710

```python
BACKEND = os.getenv("BACKEND", "ollama").lower()
DEFAULT_MODEL = (
    os.getenv("MODEL")
    or os.getenv("OLLAMA_MODEL")
    or ("gpt-4o-mini" if BACKEND == "openai" 
        else "claude-3-5-sonnet-latest" if BACKEND == "anthropic" 
        else "qwen2.5-coder:32b")
)

# Auth
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
AUTH_TOKEN_FILE = os.getenv("AUTH_TOKEN_FILE")

# Filesystem
BASE_DIR = Path(os.getenv("BASE_DIR", os.getcwd())).resolve()
ALLOW_ABSOLUTE = os.getenv("ALLOW_ABSOLUTE", "0") == "1"
ALLOW_SUDO = os.getenv("ALLOW_SUDO", "0") == "1"

# Rate limiting
FS_EXEC_MAX_REQUESTS_PER_MINUTE = int(os.getenv("FS_EXEC_MAX_REQUESTS_PER_MINUTE", "120"))
FS_EXEC_WINDOW_SECONDS = int(os.getenv("FS_EXEC_WINDOW_SECONDS", "60"))

# Memory
MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "1") == "1"
MEMORY_LESSON_LIMIT = int(os.getenv("MEMORY_LESSON_LIMIT", "3"))

# Logging
OBS_LOG_PATH: Optional[Path] = ...
```

---

## OpenAI-Compatible Endpoints

### /v1/chat/completions (Streaming & Non-Streaming)
**Lines:** 431-588

Request handling includes:
1. Extract model and messages
2. Build lesson context
3. Insert lessons into system prompt
4. Call backend (Ollama/OpenAI/Anthropic)
5. Log event and record in memory
6. Generate auto-lesson

Example response format:
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1729023456,
  "model": "qwen2.5-coder:32b",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "..."},
      "finish_reason": "stop"
    }
  ],
  "usage": {...}
}
```

---

## Security Configuration in trapdoor.json

**File:** `/Users/patricksomerville/Desktop/Trapdoor/config/trapdoor.json`

```json
{
  "app": {
    "port": 8080,
    "backend": "ollama",
    "model": "qwen2.5-coder:32b",
    "base_dir": "/",
    "allow_absolute": true,
    "allow_sudo": true
  },
  "auth": {
    "token_file": "/Users/patricksomerville/Desktop/auth_token.txt",
    "keychain_service": "TrapdoorToolsToken",
    "keychain_account": "trapdoor"
  }
}
```

---

## Token Management Scripts

### manage_auth_token.sh
**File:** `/Users/patricksomerville/Desktop/Trapdoor/scripts/manage_auth_token.sh`

Key functions:
- `generate_token()` - Create 32-character hex token
- `ensure_entry()` - Create/sync keychain entry
- `rotate_entry()` - Generate and store new token
- `print_entry()` - Display current token
- `delete_entry()` - Remove keychain entry

**Usage:**
```bash
bash scripts/manage_auth_token.sh ensure-file    # Sync keychain → file
bash scripts/manage_auth_token.sh rotate         # Generate new token
bash scripts/manage_auth_token.sh print          # Display token
bash scripts/manage_auth_token.sh delete         # Remove entry
```

---

## Key Security Functions Summary

| Function | Purpose | Security Impact |
|----------|---------|-----------------|
| `_require_auth()` | Validate Bearer token | Protects /fs/*, /exec endpoints |
| `_resolve_path()` | Escape path traversal | Prevents ../../../ attacks |
| `_enforce_rate_limit()` | Limit requests per token | DOS protection |
| `_token_fingerprint()` | Hash token for logging | Avoids logging full tokens |
| `_log_event()` | Audit log to JSONL | Compliance & debugging |
| `_build_lesson_context()` | Retrieve learned lessons | Improves accuracy |
| `_memory_record()` | Store event in memory | Learning system |

---

