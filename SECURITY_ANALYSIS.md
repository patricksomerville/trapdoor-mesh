# Trapdoor Codebase Analysis
## Security Architecture, Authentication & Request Handling

**Date:** October 28, 2025  
**Repository:** `/Users/patricksomerville/Desktop/Trapdoor`  
**Main Server:** `/Users/patricksomerville/Desktop/local_agent_server.py` (1,287 lines)

---

## Executive Summary

Trapdoor is a **token-protected bridge** that allows cloud-based agents (Genspark, Manus, etc.) to safely interact with a local machine via:

1. **OpenAI-compatible chat endpoint** (`/v1/chat/completions`) - NO AUTH REQUIRED
2. **Tool endpoints** (`/fs/*` and `/exec`) - TOKEN REQUIRED via Bearer header
3. **Memory system** - Automatically surfaces relevant lessons in system prompts

The architecture uses:
- **FastAPI** for HTTP routing with CORS enabled
- **Bearer token authentication** for filesystem/exec operations
- **Rate limiting** via token fingerprinting (SHA256 hash)
- **Audit logging** to structured JSON (JSONL format)
- **Lesson learning system** that surfaces relevant context in future requests

---

## 1. Main Server Implementation

### Location
- **Wrapper:** `/Users/patricksomerville/Desktop/openai_compatible_server.py` (thin wrapper)
- **Real implementation:** `/Users/patricksomerville/Desktop/local_agent_server.py`
- **Entry point:** `uvicorn.run(app, host="0.0.0.0", port=port)`

### Initialization
```python
TRAPDOOR_REPO_DIR = Path(os.getenv("TRAPDOOR_REPO_DIR", 
                         str(Path.home() / "Desktop" / "Trapdoor")))
```

The server auto-discovers the Trapdoor directory and imports the memory module if available.

### FastAPI Configuration
- **CORS:** Fully open (`allow_origins=["*"]`)
- **Backends:** Ollama (default), OpenAI, Anthropic
- **Default model:** `qwen2.5-coder:32b` (Ollama)
- **Configuration source:** Environment variables + `config/trapdoor.json`

---

## 2. Authentication System

### 2.1 Token Management

**Configuration files:**
- Keychain service: `TrapdoorToolsToken` (macOS keychain)
- Token file: `/Users/patricksomerville/Desktop/auth_token.txt`
- Token format: 32-character hex string (e.g., `12004c305ab471883d9e49788503485e`)

**Generation:**
```bash
# Script: scripts/manage_auth_token.sh
python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
```

### 2.2 Token Loading

**Source code:** Lines 672-690 in `local_agent_server.py`

```python
AUTH_TOKEN = os.getenv("AUTH_TOKEN")  # Single token or comma-separated list
AUTH_TOKEN_FILE = os.getenv("AUTH_TOKEN_FILE")  # File path with one token per line

AUTH_TOKENS: Set[str] = set()

# Load from environment
if AUTH_TOKEN:
    for t in AUTH_TOKEN.split(","):
        t = t.strip()
        if t:
            AUTH_TOKENS.add(t)

# Load from file
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

**Currently configured:**
- Via environment variable or file specified in `config/trapdoor.json`
- Default file: `/Users/patricksomerville/Desktop/auth_token.txt`
- Stored in macOS keychain service: `TrapdoorToolsToken`

### 2.3 Token Validation (Authentication Check)

**Function:** `_require_auth()` - Lines 845-856

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

**Key behaviors:**
1. Returns `None` (no rate limiting) if `AUTH_TOKENS` is empty
2. Returns 401 if header is missing/invalid format
3. Returns 403 if token doesn't match any in `AUTH_TOKENS` set
4. Returns token fingerprint for rate limiting tracking

**Authentication bypass:** ⚠️ If no `AUTH_TOKEN` or `AUTH_TOKEN_FILE` is set, ALL token checks are skipped

### 2.4 Token Fingerprinting

**Function:** `_token_fingerprint()` - Lines 794-795

```python
def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
```

Creates a 12-character hash prefix for rate limit tracking. Allows per-token rate limiting without logging full tokens.

---

## 3. Request Handling Flow

### 3.1 Health Endpoint (No Auth)

**Route:** `GET /health`  
**Authentication:** None  
**Response:**
```json
{
  "status": "ok",
  "backend": "ollama",
  "model": "qwen2.5-coder:32b"
}
```

### 3.2 Chat Endpoints (No Auth Required)

**Routes:**
- `POST /v1/chat/completions` (OpenAI-compatible)
- `POST /v1/chat` (Custom format)
- `GET /v1/models` (List available models)

**No token validation** - these are open to all clients.

**Chat request flow:**

1. **Accept request** (ChatRequest or OAIChatRequest)
2. **Extract user messages** for memory context
3. **Build lesson context** - calls `_build_lesson_context(user_messages)`
4. **Inject lessons into system prompt**
5. **Call backend** (Ollama, OpenAI, or Anthropic)
6. **Return response** (streaming or non-streaming)
7. **Log event** to `audit.log`
8. **Record in memory** (`memory_store.record_event()`)
9. **Generate auto-lesson** (`_auto_reflect()`)

**Memory integration:** Lines 257-258
```python
lesson_context = _build_lesson_context(user_messages, tags=["chat"])
msgs = _insert_context_message(msgs, lesson_context)
```

### 3.3 Filesystem Endpoints (Token Required)

#### `/fs/ls` - List directory or file info
**Route:** `GET /fs/ls?path=<path>`  
**Auth:** Required  
**Implementation:** Lines 924-968

```python
@app.get("/fs/ls")
def fs_ls(path: Optional[str] = None, 
          authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)  # ← Auth check here
    tgt = _resolve_path(path or str(BASE_DIR))
    # ... validate and list ...
    return data
```

#### `/fs/read` - Read file contents
**Route:** `GET /fs/read?path=<path>`  
**Auth:** Required  
**Implementation:** Lines 971-1004

Handles both text and binary files:
- Text files: Returns `{"path": str, "content": str}`
- Binary files: Returns `{"path": str, "bytes": int}` (size only)

#### `/fs/write` - Write or append to file
**Route:** `POST /fs/write`  
**Auth:** Required  
**Body:** `{"path": str, "content": str, "mode": "write" | "append"}`  
**Implementation:** Lines 1007-1027

#### `/fs/mkdir` - Create directory
**Route:** `POST /fs/mkdir`  
**Auth:** Required  
**Body:** `{"path": str, "parents": bool, "exist_ok": bool}`

#### `/fs/rm` - Remove file or directory
**Route:** `POST /fs/rm`  
**Auth:** Required  
**Body:** `{"path": str, "recursive": bool}`

### 3.4 Exec Endpoint (Token Required)

**Route:** `POST /exec`  
**Auth:** Required  
**Body:**
```json
{
  "cmd": ["command", "arg1", "arg2"],
  "cwd": "/path/to/dir",
  "timeout": 300,
  "sudo": false
}
```

**Implementation:** Lines 1082-1139

```python
@app.post("/exec")
def exec_cmd(body: ExecBody, 
             authorization: Optional[str] = Header(None)):
    token_fp = _require_auth(authorization)
    cmd = list(body.cmd)
    
    if body.sudo:
        if not ALLOW_SUDO:
            raise HTTPException(status_code=403, 
                              detail="Sudo not allowed (set ALLOW_SUDO=1)")
        cmd = ["sudo"] + cmd
    
    cwd = _resolve_path(body.cwd) if body.cwd else BASE_DIR
    
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=body.timeout or 300,
        text=True,
    )
    
    return {"cmd": cmd, "cwd": str(cwd), "rc": rc, 
            "stdout": completed.stdout, "stderr": completed.stderr}
```

**Sudo restrictions:** Requires `ALLOW_SUDO=1` env var

### 3.5 Batch Endpoint (Token Required)

**Route:** `POST /batch`  
**Auth:** Required per item (or once for batch)  
**Body:**
```json
{
  "items": [
    {"op": "fs_ls", "path": "/"},
    {"op": "fs_read", "path": "/etc/hosts"},
    {"op": "exec", "cmd": ["echo", "test"]}
  ],
  "continue_on_error": true
}
```

**Implementation:** Lines 1142-1278

Executes multiple filesystem/exec operations in sequence with per-item rate limiting (except first item).

---

## 4. Security Measures

### 4.1 Path Resolution & Escaping

**Function:** `_resolve_path()` - Lines 858-866

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

**Security features:**
1. **Tilde expansion:** `~` → user home directory
2. **Absolute path check:** Prevents `..` traversal if `ALLOW_ABSOLUTE=0`
3. **BASE_DIR restriction:** Validates resolved path is within BASE_DIR
4. **Path.resolve():** Normalizes and resolves symlinks

**Configuration:**
- `BASE_DIR` (default: current working directory)
- `ALLOW_ABSOLUTE` (default: `"0"`, false) - if true, absolute paths allowed

### 4.2 Rate Limiting

**Implementation:** Lines 812-842

```python
def _enforce_rate_limit(token: Optional[str] = None, 
                       fingerprint: Optional[str] = None) -> str:
    if fingerprint is None:
        if token is None:
            raise ValueError("token or fingerprint required")
        fingerprint = _token_fingerprint(token)
    
    if FS_EXEC_MAX_REQUESTS_PER_MINUTE <= 0 or FS_EXEC_WINDOW_SECONDS <= 0:
        return fingerprint  # Disabled if <= 0
    
    now = time.time()
    cutoff = now - FS_EXEC_WINDOW_SECONDS
    
    with _RATE_LIMIT_LOCK:
        history = _RATE_LIMIT_HISTORY.setdefault(fingerprint, deque())
        while history and history[0] < cutoff:
            history.popleft()
        
        if len(history) >= FS_EXEC_MAX_REQUESTS_PER_MINUTE:
            _log_event("rate_limit_block", token=fingerprint, ...)
            raise HTTPException(status_code=429, 
                              detail="Too many tool requests, slow down")
        history.append(now)
    
    return fingerprint
```

**Configuration:**
- `FS_EXEC_MAX_REQUESTS_PER_MINUTE` (default: `120`)
- `FS_EXEC_WINDOW_SECONDS` (default: `60`)
- Per-token tracking using fingerprint
- Thread-safe via `_RATE_LIMIT_LOCK`

**Behavior:**
- First request in batch NOT rate limited
- Subsequent items in batch ARE rate limited
- Limit disabled if either config is ≤ 0

### 4.3 Sudo Restrictions

**Configuration:** `ALLOW_SUDO` env var (default: `"0"`, false)

When `body.sudo=true`:
```python
if body.sudo:
    if not ALLOW_SUDO:
        raise HTTPException(status_code=403, 
                          detail="Sudo not allowed (set ALLOW_SUDO=1)")
    cmd = ["sudo"] + cmd
```

Allows clients to request sudo elevation, but must be explicitly enabled.

### 4.4 Audit Logging

**Path:** `.proxy_runtime/audit.log` (or `OBS_LOG_PATH`)

**Format:** JSON lines (JSONL)

**Example entry:**
```json
{
  "ts": 1729023456.789,
  "event": "exec",
  "backend": "ollama",
  "token": "abcdef123456",
  "status": "ok",
  "cmd": ["echo", "test"],
  "cwd": "/tmp",
  "rc": 0
}
```

**Logged events:**
- `chat` - Chat completions
- `fs_ls` - Directory listing
- `fs_read` - File reads
- `fs_write` - File writes
- `fs_mkdir` - Directory creation
- `fs_rm` - File/directory deletion
- `exec` - Command execution
- `batch` - Batch operations
- `auth_failure` - Failed auth attempts
- `rate_limit_block` - Rate limit exceeded

**Configuration:** `OBS_LOG_PATH` env var (empty string disables)

---

## 5. Memory & Learning System

### 5.1 Memory Storage

**Location:** `/Users/patricksomerville/Desktop/Trapdoor/memory/`

**Files:**
- `events.jsonl` - All recorded events (chat, fs, exec, etc.)
- `lessons.jsonl` - Curated long-term lessons

### 5.2 Lesson Integration in Chat

**Function:** `_build_lesson_context()` - Lines 752-769

```python
def _build_lesson_context(user_messages: List[Dict[str, Any]], 
                         tags: Optional[List[str]] = None) -> Optional[str]:
    if not (MEMORY_ENABLED and memory_store is not None):
        return None
    
    query_text = _user_text_from_messages(user_messages)
    lessons = memory_store.get_relevant_lessons(
        query_text, 
        tags=tags, 
        limit=MEMORY_LESSON_LIMIT  # Default: 3
    )
    
    body = memory_store.format_lessons_as_bullets(lessons)
    return body
```

**Configuration:**
- `MEMORY_ENABLED` (default: `"1"`)
- `MEMORY_LESSON_LIMIT` (default: `"3"`)

**How it works:**
1. Extract user text from messages
2. Search lessons.jsonl for relevant entries
3. Match by keyword overlap + tags
4. Format as bullet points
5. Inject into system message

### 5.3 Lesson Search Algorithm

**Function:** `get_relevant_lessons()` in `memory/store.py` - Lines 108-132

```python
def get_relevant_lessons(query: str, *, tags: Optional[Sequence[str]] = None, 
                        limit: int = 3) -> List[Dict[str, Any]]:
    lessons = list(_load_jsonl(LESSONS_PATH))
    query_keys = _keyword_set(query)  # Tokens > 2 chars
    
    if tags:
        query_keys.update(t.lower() for t in tags if t)
    
    scored: List[Tuple[int, float, Dict[str, Any]]] = []
    for lesson in lessons:
        lesson_text = f"{lesson.get('title','')} {lesson.get('summary','')} {' '.join(lesson.get('tags') or [])}"
        lesson_keys = _keyword_set(lesson_text)
        
        score = len(query_keys & lesson_keys)  # Intersection
        if tags and set(lesson.get("tags") or []) & set(tags):
            score += 2  # Boost if tags match
        
        if score == 0 and query_keys:
            continue
        
        scored.append((score, lesson.get("ts", 0.0), lesson))
    
    if not scored:
        return lessons[-limit:]  # Fall back to most recent
    
    top = heapq.nlargest(limit, scored, key=lambda item: (item[0], item[1]))
    return [item[2] for item in top]
```

**Scoring logic:**
- Keyword overlap (intersection) = primary score
- Tag match = +2 bonus
- Fallback: Return most recent lessons if no matches

### 5.4 Auto-Learning

**Function:** `_auto_reflect()` - Lines 776-791

After every chat request, an "auto lesson" is generated:

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

**Auto-lesson format (from store.py):**
```
Title: "Auto lesson 2025-10-28 10:30:45"
Summary: "User asked: [first 200 chars] | Response: [first 200 chars]"
Tags: ["auto"] + provided tags
```

---

## 6. Configuration System

### 6.1 Configuration File

**Location:** `/Users/patricksomerville/Desktop/Trapdoor/config/trapdoor.json`

**Structure:**
```json
{
  "app": {
    "port": 8080,
    "backend": "ollama",
    "model": "qwen2.5-coder:32b",
    "base_dir": "/",
    "allow_absolute": true,
    "allow_sudo": true,
    "default_system_prompt": "..."
  },
  "auth": {
    "token_file": "/Users/patricksomerville/Desktop/auth_token.txt",
    "keychain_service": "TrapdoorToolsToken",
    "keychain_account": "trapdoor"
  },
  "launch_agents": {
    "localproxy_label": "com.trapdoor.localproxy",
    "cloudflared_label": "com.trapdoor.cloudflared",
    "python_path": "/usr/local/bin/python3",
    "server_path": "/Users/patricksomerville/Desktop/openai_compatible_server.py",
    "working_directory": "/Users/patricksomerville/Desktop",
    "log_dir": "/Users/patricksomerville/Desktop/.proxy_runtime"
  },
  "cloudflare": {
    "token": "...",
    "tunnel_id": "...",
    "hostname": "trapdoor.treehouse.tech",
    "config_dir": "/Users/patricksomerville/.cloudflared"
  },
  "models": {
    "default_profile": "default",
    "profiles": {
      "default": {...},
      "tools": {...}
    }
  }
}
```

### 6.2 Environment Variables (Override)

**Chat/Model:**
- `BACKEND` (ollama, openai, anthropic)
- `MODEL` / `OLLAMA_MODEL`
- `DEFAULT_SYSTEM_PROMPT`

**Filesystem/Exec:**
- `BASE_DIR` (default: cwd)
- `ALLOW_ABSOLUTE` (default: 0)
- `ALLOW_SUDO` (default: 0)

**Authentication:**
- `AUTH_TOKEN` (single or comma-separated)
- `AUTH_TOKEN_FILE` (path to file with one token per line)

**Rate Limiting:**
- `FS_EXEC_MAX_REQUESTS_PER_MINUTE` (default: 120)
- `FS_EXEC_WINDOW_SECONDS` (default: 60)

**Memory:**
- `TRAPDOOR_MEMORY_DIR` (default: `Trapdoor/memory/`)
- `TRAPDOOR_REPO_DIR` (default: `~/Desktop/Trapdoor`)
- `MEMORY_ENABLED` (default: 1)
- `MEMORY_LESSON_LIMIT` (default: 3)

**Logging:**
- `OBS_LOG_PATH` (default: `.proxy_runtime/audit.log`, empty string disables)

---

## 7. Current Security Issues & Gaps

### Critical Issues

1. **No Authentication on Chat Endpoints** ⚠️⚠️⚠️
   - `/v1/chat/completions` accepts all requests
   - System prompt exposed (includes model info, suggested endpoints)
   - Can be used for prompt injection

2. **Authentication Bypass if Misconfigured** ⚠️⚠️
   - If `AUTH_TOKEN` and `AUTH_TOKEN_FILE` are both unset, filesystem/exec endpoints are fully open
   - No default token - depends on operator setup

3. **No Scoped Permissions** ⚠️⚠️
   - All tokens have full access (fs_*, exec, batch)
   - No per-operation scoping (read-only, write-only, specific paths)
   - Can't grant different tokens different capabilities

4. **Broad Path Restrictions Only** ⚠️
   - Path restriction to `BASE_DIR` is all-or-nothing
   - Can't restrict specific sensitive paths
   - `ALLOW_ABSOLUTE=true` allows unrestricted access

5. **Single Token Per Connection** ⚠️
   - No multi-token system (per-operation, per-partner, rotation)
   - Token rotation requires restart
   - No token expiration/TTL

6. **Basic Rate Limiting** ⚠️
   - Per-token limit but not per-operation
   - No differentiation (read ops vs write ops)
   - Window-based, not sliding window

7. **Verbose Audit Logging** ⚠️
   - Logs full command arguments (potential command injection attempts)
   - Logs file paths and content summaries
   - Could leak sensitive data if logs are exposed

8. **No Input Validation** ⚠️
   - `subprocess.run()` receives user-supplied cmd list directly
   - Relies on caller not passing injection
   - No command allowlist

9. **Timeout as Only DOS Protection** ⚠️
   - Default 300s timeout vulnerable to resource exhaustion
   - No memory limits on output capture
   - Large file reads not limited

10. **Memory System Accessible via Logs** ⚠️
    - `memory/events.jsonl` contains prompts and responses
    - `memory/lessons.jsonl` may contain sensitive info
    - Shared between all tokens/users

---

## 8. Current Strengths

✓ **Bearer token authentication** on tool endpoints  
✓ **Rate limiting** per token  
✓ **Path escaping** prevents directory traversal  
✓ **Sudo restrictions** (must be explicitly enabled)  
✓ **Audit logging** to structured JSON  
✓ **Memory system** learns from interactions  
✓ **Timeout protection** on exec  
✓ **CORS isolation** (token required for tools)  

---

## 9. Recommended Security Improvements

### Phase 1: Token System Enhancement
1. **Scoped tokens** - permissions per token (read, write, exec)
2. **Token expiration** - TTL or rotation schedule
3. **Token families** - group related tokens, rotate all
4. **Token metadata** - name, created date, last used, scope

### Phase 2: Path & Command Controls
1. **Path allowlists** per token
2. **Path denylists** (e.g., /etc, /var, ~/.ssh)
3. **Command allowlists** per token (specific binaries)
4. **Command denylists** (dangerous commands)

### Phase 3: Rate & Resource Limits
1. **Per-operation rate limits** (fs_read vs fs_write)
2. **Output size limits** (max response bytes)
3. **Memory limits** for subprocess
4. **Per-token daily/monthly quotas**

### Phase 4: Audit & Compliance
1. **Redact sensitive data** from logs
2. **Structured audit** with request/response hashing
3. **Alert rules** for suspicious patterns
4. **Compliance export** (for logging requirements)

---

## 10. File Structure Reference

```
/Users/patricksomerville/Desktop/
├── openai_compatible_server.py       # Thin wrapper
├── local_agent_server.py             # Main server (1,287 lines)
├── auth_token.txt                    # Current bearer token
└── Trapdoor/
    ├── README.md                     # Getting started
    ├── AGENTS.md                     # Developer guidelines
    ├── ACCESS_PACK.txt               # Partner handoff
    ├── config/
    │   ├── trapdoor.json             # Configuration
    │   └── templates/                # Plist + config templates
    ├── memory/
    │   ├── __init__.py
    │   ├── store.py                  # Memory implementation
    │   ├── events.jsonl              # All events log
    │   └── lessons.jsonl             # Curated lessons
    ├── scripts/
    │   ├── start_proxy_and_tunnel.sh
    │   ├── manage_auth_token.sh      # Token rotation
    │   ├── check_health.sh           # Health checks
    │   ├── generate_access_pack.sh   # Partner pack
    │   ├── self_test.sh              # Smoke test
    │   └── render_configs.py         # Config rendering
    ├── plists/                       # LaunchAgent definitions
    ├── templates/                    # Plist & config templates
    ├── control_panel.py              # Non-tech operator menu
    └── .proxy_runtime/               # Runtime artifacts
        ├── audit.log                 # Structured audit log
        ├── public_url.txt            # Cloudflare tunnel URL
        ├── packs/                    # Generated access packs
        └── *.pid                     # Process IDs
```

---

## 11. Request Flow Diagrams

### Chat Request (No Auth)
```
Client → POST /v1/chat/completions
         ↓
         Parse request (no token check)
         ↓
         Extract user messages
         ↓
         Build lesson context (search memory)
         ↓
         Inject lessons into system prompt
         ↓
         Call backend (Ollama/OpenAI/Anthropic)
         ↓
         Stream or return response
         ↓
         Log event (chat)
         ↓
         Record in memory (events.jsonl)
         ↓
         Generate auto lesson
         ↓
         Response → Client
```

### Tool Request (Token Required)
```
Client → GET /fs/ls?path=/ with Authorization: Bearer <token>
         ↓
         Extract & validate token
         ↓
         Check rate limit (token fingerprint)
         ↓
         Resolve path (escape traversal)
         ↓
         Check BASE_DIR restriction
         ↓
         Execute operation (ls, read, write, mkdir, rm, exec)
         ↓
         Log event (fs_ls, exec, etc.) with token fingerprint
         ↓
         Record in memory
         ↓
         Response → Client
```

### Batch Request (Token Required)
```
Client → POST /batch with Authorization: Bearer <token>
         ↓
         Validate token once
         ↓
         For each item in batch:
           ├─ (Skip rate limit for first item)
           ├─ Rate limit check (items 2+)
           ├─ Execute operation (fs_ls, fs_read, etc.)
           ├─ Collect result or error
           └─ Continue if continue_on_error=true
         ↓
         Log batch event (status, counts)
         ↓
         Record in memory
         ↓
         Response with per-item results → Client
```

---

## 12. Security Configuration Checklist

### Before Production Deployment

- [ ] Generate unique token (not the default)
- [ ] Store token in keychain (not plaintext)
- [ ] Set `BASE_DIR` to restricted location (not `/`)
- [ ] Set `ALLOW_ABSOLUTE=false` (not true)
- [ ] Set `ALLOW_SUDO=false` (unless required)
- [ ] Enable `OBS_LOG_PATH` for audit logging
- [ ] Set `FS_EXEC_MAX_REQUESTS_PER_MINUTE` appropriately
- [ ] Configure `DEFAULT_SYSTEM_PROMPT` to document auth requirements
- [ ] Review `memory/lessons.jsonl` for sensitive data before sharing
- [ ] Test health checks and self-test before deploying tunnel
- [ ] Rotate tokens before granting access to external agents
- [ ] Monitor audit.log for anomalies

---

## Key Takeaways

1. **Trapdoor is a developer tool**, not a zero-trust system
2. **Chat is open**, tools are token-protected via Bearer auth
3. **Memory system** automatically learns from interactions
4. **Rate limiting** exists but is basic (per-token, window-based)
5. **Path escaping** prevents traversal within BASE_DIR
6. **Audit logging** is comprehensive and structured
7. **Token management** uses macOS keychain for security
8. **Configuration** is environment-driven with JSON defaults

**The system is suitable for:**
- Granting cloud agents (Manus, Genspark) local machine access
- Learning & improving over time via memory system
- Basic rate limiting and path restrictions

**Not suitable for:**
- Multi-tenant environments
- Zero-trust security models
- Fine-grained permission control
- Regulatory compliance (audit trails exist but need hardening)
