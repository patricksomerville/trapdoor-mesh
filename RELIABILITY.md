# Reliability: Make It Work Smoothly Every Time

**Goal:** Trapdoor works perfectly regardless of LLM backend or cloud agent

**Focus:** Robustness, consistency, graceful degradation

---

## The Problems

### Backend Issues
- Ollama might be down
- OpenAI API might fail
- Anthropic API might fail
- Network timeouts
- Model not available

### Cloud Tunnel Issues
- Cloudflare tunnel goes down
- Network connectivity issues
- Tunnel authentication fails

### Inconsistencies
- Different backends return different formats
- Error handling varies
- Timeouts differ
- Authentication failures unclear

---

## Solutions: Make It Bulletproof

### 1. Automatic Backend Fallback

**Problem:** If Ollama fails, everything breaks

**Solution:** Automatic fallback chain

```python
# Try backends in order until one works
BACKEND_FALLBACK_CHAIN = ["ollama", "openai", "anthropic"]

def chat_with_fallback(model, messages):
    last_error = None
    for backend in BACKEND_FALLBACK_CHAIN:
        try:
            return chat_with_backend(backend, model, messages)
        except Exception as e:
            last_error = e
            continue
    raise HTTPException(status_code=503, detail=f"All backends failed. Last error: {last_error}")
```

**Why:** If one backend fails, automatically try next

---

### 2. Consistent Response Format

**Problem:** Different backends return different formats

**Solution:** Normalize all responses

```python
def normalize_response(backend, raw_response):
    """Convert any backend response to consistent format"""
    if backend == "ollama":
        return {"content": raw_response.get("message", {}).get("content", ""), "model": raw_response.get("model", "")}
    elif backend == "openai":
        return {"content": raw_response.get("choices", [{}])[0].get("message", {}).get("content", ""), "model": raw_response.get("model", "")}
    elif backend == "anthropic":
        return {"content": "".join([p.get("text", "") for p in raw_response.get("content", [])]), "model": raw_response.get("model", "")}
    return raw_response
```

**Why:** Cloud agents see consistent format regardless of backend

---

### 3. Health Monitoring

**Problem:** Don't know if backend is healthy until it fails

**Solution:** Continuous health checks

```python
class BackendHealthMonitor:
    def __init__(self):
        self.backend_status = {}
        self.check_interval = 60  # seconds
        
    def check_backend(self, backend):
        """Check if backend is healthy"""
        try:
            if backend == "ollama":
                ollama.list()
                return True
            elif backend == "openai":
                # Quick health check
                requests.get("https://api.openai.com/v1/models", timeout=5)
                return True
            elif backend == "anthropic":
                # Quick health check
                requests.get("https://api.anthropic.com/v1/messages", timeout=5)
                return True
        except:
            return False
    
    def get_healthy_backends(self):
        """Return list of healthy backends"""
        return [b for b in BACKEND_FALLBACK_CHAIN if self.check_backend(b)]
```

**Why:** Know which backends are available before using them

---

### 4. Retry Logic

**Problem:** Transient failures cause permanent errors

**Solution:** Automatic retries with exponential backoff

```python
def chat_with_retry(backend, model, messages, max_retries=3):
    """Retry on transient failures"""
    for attempt in range(max_retries):
        try:
            return chat_with_backend(backend, model, messages)
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
        except Exception as e:
            # Non-retryable error
            raise
```

**Why:** Handle temporary network issues automatically

---

### 5. Graceful Degradation

**Problem:** If features fail, everything breaks

**Solution:** Degrade gracefully

```python
# If memory system fails, continue without it
try:
    lesson_context = _build_lesson_context(user_messages)
except Exception:
    lesson_context = None  # Continue without context

# If workflow tracking fails, continue without it
try:
    tracker = WorkflowTracker(user_intent)
except Exception:
    tracker = None  # Continue without tracking
```

**Why:** Core functionality works even if optional features fail

---

### 6. Better Error Messages

**Problem:** Errors are confusing

**Solution:** Clear, actionable error messages

```python
def handle_backend_error(backend, error):
    """Convert backend errors to clear messages"""
    if isinstance(error, requests.Timeout):
        return "Backend timed out. Try again or switch backend."
    elif isinstance(error, requests.ConnectionError):
        return f"{backend} backend unreachable. Check network."
    elif "model not found" in str(error):
        return f"Model not available on {backend}. Check model name."
    else:
        return f"{backend} error: {error}"
```

**Why:** Know what went wrong and how to fix it

---

### 7. Connection Pooling

**Problem:** Each request creates new connection

**Solution:** Reuse connections

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

**Why:** Faster, more reliable connections

---

### 8. Cloud Tunnel Health

**Problem:** Cloudflare tunnel might be down

**Solution:** Monitor tunnel health

```python
def check_tunnel_health():
    """Check if tunnel is working"""
    try:
        response = requests.get("https://trapdoor.treehouse.tech/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Auto-restart tunnel if down
if not check_tunnel_health():
    restart_tunnel()
```

**Why:** Tunnel stays up automatically

---

### 9. Model Availability Check

**Problem:** Model might not be available on backend

**Solution:** Check before using

```python
def ensure_model_available(backend, model):
    """Ensure model is available before using"""
    if backend == "ollama":
        models = ollama.list().get("models", [])
        model_names = [m.get("name", "") for m in models]
        if model not in model_names:
            # Auto-pull model
            ollama.pull(model)
    elif backend == "openai":
        # Check if model exists in OpenAI's list
        # (or just try and handle error)
        pass
```

**Why:** Models are ready when needed

---

### 10. Unified Error Handling

**Problem:** Different error handling for each backend

**Solution:** Unified error handler

```python
@catch_all_errors
def chat_endpoint(request):
    """Unified chat endpoint with error handling"""
    try:
        return chat_with_fallback(request.model, request.messages)
    except BackendUnavailableError as e:
        return {"error": f"Backend unavailable: {e}", "suggestions": ["Try different backend", "Check network"]}
    except ModelNotFoundError as e:
        return {"error": f"Model not found: {e}", "suggestions": ["Check model name", "Try different model"]}
    except Exception as e:
        return {"error": f"Unknown error: {e}", "suggestions": ["Check logs", "Try again"]}
```

**Why:** Consistent error handling regardless of backend

---

## Implementation Priority

### Do First (Critical):
1. ✅ **Automatic backend fallback** - Don't fail if one backend down
2. ✅ **Consistent response format** - Same format regardless of backend
3. ✅ **Better error messages** - Know what went wrong

### Do Next (Important):
4. ✅ **Retry logic** - Handle transient failures
5. ✅ **Health monitoring** - Know backend status
6. ✅ **Graceful degradation** - Core works even if features fail

### Do When Needed:
7. ✅ **Connection pooling** - Performance/reliability
8. ✅ **Tunnel health** - Keep tunnel up
9. ✅ **Model availability** - Ensure models ready
10. ✅ **Unified error handling** - Consistency

---

## The Goal

**Make it so:**
- ✅ Works regardless of which LLM backend
- ✅ Works regardless of which cloud agent
- ✅ Handles failures gracefully
- ✅ Provides clear error messages
- ✅ Recovers automatically
- ✅ Degrades gracefully

**Result:** Just works. Every time.

---

## Quick Wins

**1. Add backend fallback (30 min)**
```python
# In chat endpoint, try backends in order
backends = ["ollama", "openai", "anthropic"]
for backend in backends:
    try:
        return chat_with_backend(backend, ...)
    except:
        continue
```

**2. Normalize responses (15 min)**
```python
# After getting response, normalize format
normalized = normalize_response(backend, raw_response)
```

**3. Better error messages (15 min)**
```python
# Replace generic errors with clear messages
raise HTTPException(500, detail=f"{backend} backend failed: {error}. Try different backend.")
```

**Total: 1 hour to make it much more reliable**

---

**Focus:** Make it bulletproof. Just works. Every time.

