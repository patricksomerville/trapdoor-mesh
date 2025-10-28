# Trapdoor Codebase Exploration - Summary Report

**Date:** October 28, 2025  
**Repository:** `/Users/patricksomerville/Desktop/Trapdoor`  
**Exploration Scope:** Complete security audit, authentication system, request handling flow

---

## What Was Explored

### 1. Core Server Architecture
- **Main server:** `/Users/patricksomerville/Desktop/local_agent_server.py` (1,287 lines)
- **Wrapper:** `/Users/patricksomerville/Desktop/openai_compatible_server.py`
- **Framework:** FastAPI (async HTTP, CORS enabled)
- **Backends:** Ollama (default), OpenAI, Anthropic

### 2. Authentication System
- **Token format:** 32-character hex string (e.g., `12004c305ab471883d9e49788503485e`)
- **Storage:** macOS keychain service `TrapdoorToolsToken`
- **File storage:** `/Users/patricksomerville/Desktop/auth_token.txt`
- **Loading:** Environment variables or file-based
- **Validation:** Bearer token header check (`Authorization: Bearer <token>`)

### 3. Endpoint Request Handling

#### Chat Endpoints (No Auth Required)
- `POST /v1/chat/completions` - OpenAI-compatible
- `POST /v1/chat` - Custom format
- `GET /v1/models` - List models
- `GET /health` - Service health

**Flow:**
1. Accept request
2. Extract user messages
3. Build lesson context (search memory)
4. Inject lessons into system prompt
5. Call backend (Ollama/OpenAI/Anthropic)
6. Return response (stream or non-stream)
7. Log event
8. Record in memory
9. Generate auto-lesson

#### Tool Endpoints (Token Required)
- `GET /fs/ls?path=<path>` - List directory
- `GET /fs/read?path=<path>` - Read file
- `POST /fs/write` - Write/append file
- `POST /fs/mkdir` - Create directory
- `POST /fs/rm` - Delete file/directory
- `POST /exec` - Execute command
- `POST /batch` - Multiple operations

**Security checks per operation:**
1. Token validation (`_require_auth()`)
2. Rate limit check (`_enforce_rate_limit()`)
3. Path resolution & escaping (`_resolve_path()`)
4. BASE_DIR boundary check
5. Sudo restrictions (if enabled)
6. Audit logging

### 4. Security Mechanisms

#### Authentication
- Bearer token validation (RFC 7235)
- Token set loaded from env + file
- 401/403 error responses on failure
- Tokenless requests rejected if tokens configured

#### Rate Limiting
- Per-token based on 12-char SHA256 fingerprint
- Window-based (default: 120 requests per 60 seconds)
- Thread-safe via locking
- Disabled if config ≤ 0
- First batch item exempt, subsequent items limited

#### Path Escaping
- Tilde expansion (`~` → home)
- Path normalization (resolve symlinks)
- BASE_DIR boundary enforcement
- Prevents `../../../` traversal attacks
- Optional absolute path restriction

#### Audit Logging
- Structured JSON lines (JSONL)
- Default: `.proxy_runtime/audit.log`
- Configurable via `OBS_LOG_PATH`
- Logs: events, tokens (fingerprinted), status, duration
- Thread-safe appending

### 5. Memory & Learning System

#### Storage
- `memory/events.jsonl` - All events
- `memory/lessons.jsonl` - Curated lessons

#### Automatic Integration
- Extract user messages from each chat request
- Search lessons by keyword overlap + tags
- Inject top 3 lessons into system prompt
- Generate "auto lesson" after response
- Keyword scoring with tag boost (+2)

#### Learning Features
- Keyword-based lesson retrieval
- Tag-based filtering
- Recency fallback (if no matches)
- Configurable limit (default: 3 lessons)
- Optional via `MEMORY_ENABLED` env var

### 6. Configuration System

#### Configuration File
- **Location:** `config/trapdoor.json`
- **Sections:** app, auth, launch_agents, cloudflare, models
- **Controls:** port, backend, model, base_dir, allow_absolute, allow_sudo

#### Environment Variable Overrides
- `BACKEND`, `MODEL`, `DEFAULT_SYSTEM_PROMPT`
- `BASE_DIR`, `ALLOW_ABSOLUTE`, `ALLOW_SUDO`
- `AUTH_TOKEN`, `AUTH_TOKEN_FILE`
- `FS_EXEC_MAX_REQUESTS_PER_MINUTE`, `FS_EXEC_WINDOW_SECONDS`
- `MEMORY_ENABLED`, `MEMORY_LESSON_LIMIT`
- `OBS_LOG_PATH`, `TRAPDOOR_REPO_DIR`, `TRAPDOOR_MEMORY_DIR`

---

## Key Files & Line References

| File | Purpose | Key Lines |
|------|---------|-----------|
| `local_agent_server.py` | Main server (1,287 lines) | See CODE_REFERENCE.md |
| `config/trapdoor.json` | Configuration | Port, auth, model settings |
| `memory/store.py` | Memory implementation | Lesson search algorithm |
| `scripts/manage_auth_token.sh` | Token management | Generate, rotate, delete |
| `scripts/check_health.sh` | Health validation | Test all endpoints |
| `control_panel.py` | Operator UI | Non-technical menu |
| `README.md` | Getting started | Operation guide |
| `AGENTS.md` | Developer guidelines | Coding style, testing |

---

## Security Analysis Summary

### Current Strengths ✓
1. Bearer token authentication on tool endpoints
2. Per-token rate limiting with fingerprinting
3. Path traversal prevention via escaping
4. Structured audit logging (JSONL)
5. Sudo restrictions (explicit enable required)
6. Comprehensive memory/learning system
7. Timeout protection on commands
8. Multi-backend support (Ollama/OpenAI/Anthropic)

### Critical Security Gaps ⚠️
1. **No authentication on chat** - `/v1/chat/completions` is fully open
2. **Authentication bypass if misconfigured** - Empty AUTH_TOKENS disables checks
3. **No scoped permissions** - All tokens have full access
4. **No path allowlists/denylists** - Only BASE_DIR restriction
5. **Single token per connection** - No multi-token system
6. **Verbose audit logs** - Full commands and paths logged
7. **No input validation** - Commands accepted as-is
8. **Memory accessible to all tokens** - Lessons shared across users
9. **No token expiration** - Tokens valid indefinitely
10. **Timeout-only DOS protection** - No memory/output limits

### Recommended Improvements (Phased)
**Phase 1:** Token system enhancement (scopes, expiration, metadata)  
**Phase 2:** Path & command controls (allowlists, denylists)  
**Phase 3:** Rate & resource limits (per-op, output size, quotas)  
**Phase 4:** Audit & compliance (redaction, hashing, alerts)  

---

## How to Use This Documentation

### For Security Review
- Start with **SECURITY_ANALYSIS.md** for threat overview
- Review **Security Issues & Gaps** section for specific concerns
- Check **CODE_REFERENCE.md** for implementation details
- Compare current config against **Security Configuration Checklist**

### For Implementation
- Follow **CODE_REFERENCE.md** for line-by-line implementation
- Use **Request Flow Diagrams** to understand data flow
- Reference **Configuration System** for env var overrides
- Check **File Structure Reference** for file organization

### For Integration
- Review **ACCESS_PACK.txt** for client connection details
- Follow **Token Management** scripts for key rotation
- Check **Health Endpoint** for validation
- Monitor **Audit Logging** for anomalies

---

## Generated Documentation

The following files have been created in this exploration:

1. **SECURITY_ANALYSIS.md** (This Directory)
   - Comprehensive security architecture analysis
   - Detailed authentication and request flow documentation
   - 12 security issue categories with risk assessment
   - Phased improvement recommendations
   - 450+ lines of detailed analysis

2. **CODE_REFERENCE.md** (This Directory)
   - Line-by-line code references for all security features
   - Function signatures and implementation details
   - Configuration file structure
   - Script usage examples
   - Security function summary table

3. **EXPLORATION_SUMMARY.md** (This File)
   - Quick reference guide
   - File index with line numbers
   - Strengths and gaps overview
   - Documentation usage guide

---

## Next Steps

### To Implement Security Improvements
1. Review SECURITY_ANALYSIS.md § 7 for all identified issues
2. Prioritize issues by severity (3 critical, 2 high, 5 medium)
3. Reference CODE_REFERENCE.md for implementation locations
4. Test using existing scripts (check_health.sh, self_test.sh)
5. Update audit.log monitoring for security events

### To Deploy Safely
1. Generate unique token (not default)
2. Store in keychain via manage_auth_token.sh
3. Set BASE_DIR to restricted location
4. Disable ALLOW_ABSOLUTE and ALLOW_SUDO
5. Enable OBS_LOG_PATH for audit logging
6. Run health check before tunnel deployment
7. Rotate token before granting external access
8. Monitor audit.log for anomalies

### To Understand Codebase
1. Start with health endpoint (GET /health)
2. Review chat endpoint flow (no auth required)
3. Study fs endpoints (token required, path escaping)
4. Examine exec endpoint (command execution, sudo)
5. Trace memory system (lesson injection, auto-learning)
6. Review rate limiting (fingerprinting, window-based)

---

## Quick Reference: Security Functions

```python
_require_auth(authorization: Optional[str])
  → Validates Bearer token
  → Returns token fingerprint for rate limiting
  → Raises 401/403 on failure

_resolve_path(path: str) -> Path
  → Escapes path traversal attacks
  → Enforces BASE_DIR restriction
  → Normalizes symlinks

_enforce_rate_limit(token: Optional[str]) -> str
  → Tracks requests per token fingerprint
  → Uses sliding window (default: 120/60s)
  → Thread-safe via locking

_token_fingerprint(token: str) -> str
  → SHA256 hash first 12 chars
  → Allows per-token tracking without logging full token

_log_event(event: str, **payload: Any)
  → Appends JSON to audit.log
  → Safe failure (exception caught)
  → Can be disabled with OBS_LOG_PATH=""

_build_lesson_context(user_messages: List[Dict]) -> Optional[str]
  → Searches lessons.jsonl for relevant entries
  → Scores by keyword overlap + tag match
  → Returns formatted bullet points for system prompt
```

---

## File Sizes & Complexity

| Component | Size | Complexity |
|-----------|------|------------|
| local_agent_server.py | 1,287 lines | High (fastapi, streaming, multiple backends) |
| memory/store.py | ~150 lines | Medium (JSONL I/O, keyword scoring) |
| scripts/*.sh | 200-300 lines each | Medium (shell scripting, environment setup) |
| control_panel.py | 442 lines | Medium (menu-driven UI, subprocess calls) |
| config/trapdoor.json | ~50 lines | Low (JSON configuration) |

---

## Summary

Trapdoor is a well-structured **developer tool** for granting cloud agents local machine access with:

- ✓ Token-protected filesystem & command execution
- ✓ Memory system that learns from interactions
- ✓ Comprehensive audit logging
- ✓ Path traversal protection
- ✓ Basic rate limiting

But it **lacks** fine-grained security controls for production environments:

- ✗ No scoped permissions per token
- ✗ No path/command allowlists
- ✗ No token expiration
- ✗ No input validation
- ✗ Open chat endpoints

**Suitable for:** Individual developers granting agent access, learning systems, basic automation  
**Not suitable for:** Multi-tenant systems, regulatory compliance, zero-trust architectures

---

**Exploration completed by:** Security analysis tools  
**Documentation version:** 1.0  
**Last updated:** October 28, 2025

