# Trapdoor Connection Information

## For AI Agents (OpenAI-Compatible)

**API Base URL:**
```
https://celsa-nonsimulative-wyatt.ngrok-free.dev
```

**Authentication Token:**
```
90ac04027a0b4aba685dcae29eeed91a
```

**Authorization Header:**
```
Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a
```

---

## Chat Endpoint (OpenAI-Compatible)

**Endpoint:** `POST /v1/chat/completions`

**Example Request:**
```bash
curl -X POST https://celsa-nonsimulative-wyatt.ngrok-free.dev/v1/chat/completions \
  -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:32b",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

---

## Filesystem & Exec Tools

### List Directory
```bash
GET /fs/ls?path=/Users/patricksomerville/Desktop
```

### Read File
```bash
GET /fs/read?path=/Users/patricksomerville/Desktop/file.txt
```

### Write File
```bash
POST /fs/write
Body: {"path": "/path/to/file.txt", "content": "file contents"}
```

### Execute Command
```bash
POST /exec
Body: {"path": "/working/directory", "command": ["ls", "-la"]}
```

---

## Quick Setup for ChatGPT/Claude/etc.

**Just provide these two values:**

1. **API URL:** `https://celsa-nonsimulative-wyatt.ngrok-free.dev`
2. **Token:** `90ac04027a0b4aba685dcae29eeed91a`

The agent will automatically have access to:
- Chat completions (OpenAI-compatible)
- Filesystem operations (read, write, list, mkdir, rm)
- Command execution
- Token management (admin scope)

---

## Security Scopes

Your current token has **admin** scope, which grants:
- ✅ Full filesystem access
- ✅ Command execution (including sudo)
- ✅ Token management
- ✅ Approval workflows
- ✅ No rate limits (120 req/min)

---

## Health Check

Test connectivity:
```bash
curl https://celsa-nonsimulative-wyatt.ngrok-free.dev/health
```

Expected response:
```json
{"status":"ok","backend":"ollama","model":"qwen2.5-coder:32b"}
```

---

**Last Updated:** 2025-10-28 11:56 AM
**Status:** 🟢 ONLINE
