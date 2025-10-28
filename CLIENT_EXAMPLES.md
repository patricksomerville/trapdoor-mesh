# Trapdoor Client Examples

## Python (OpenAI SDK)

### Basic Chat
```python
from openai import OpenAI

client = OpenAI(
    api_key="90ac04027a0b4aba685dcae29eeed91a",
    base_url="https://celsa-nonsimulative-wyatt.ngrok-free.dev/v1"
)

resp = client.chat.completions.create(
    model="qwen2.5-coder:32b",
    messages=[{"role": "user", "content": "ping"}]
)
print(resp.choices[0].message.content)
```

### With Filesystem Tools
```python
import requests

base_url = "https://celsa-nonsimulative-wyatt.ngrok-free.dev"
headers = {"Authorization": "Bearer 90ac04027a0b4aba685dcae29eeed91a"}

# List directory
resp = requests.get(f"{base_url}/fs/ls",
    params={"path": "/Users/patricksomerville/Desktop"},
    headers=headers
)
files = resp.json()
print(f"Found {len(files)} items")

# Read file
resp = requests.get(f"{base_url}/fs/read",
    params={"path": "/Users/patricksomerville/Desktop/test.txt"},
    headers=headers
)
content = resp.json()
print(content)

# Write file
resp = requests.post(f"{base_url}/fs/write",
    json={
        "path": "/Users/patricksomerville/Desktop/output.txt",
        "content": "Hello from remote agent!"
    },
    headers=headers
)
print(resp.json())

# Execute command
resp = requests.post(f"{base_url}/exec",
    json={
        "path": "/Users/patricksomerville/Desktop",
        "command": ["ls", "-la"]
    },
    headers=headers
)
result = resp.json()
print(result["stdout"])
```

---

## JavaScript/Node.js (Tested Working)

### Basic Chat
```javascript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "90ac04027a0b4aba685dcae29eeed91a",
  baseURL: "https://celsa-nonsimulative-wyatt.ngrok-free.dev/v1"
});

const res = await client.chat.completions.create({
  model: "qwen2.5-coder:32b",
  messages: [{ role: "user", content: "ping" }]
});

console.log(res.choices[0].message);
```

### With Filesystem Tools
```javascript
const BASE_URL = 'https://celsa-nonsimulative-wyatt.ngrok-free.dev';
const headers = {
  'Authorization': 'Bearer 90ac04027a0b4aba685dcae29eeed91a',
  'Content-Type': 'application/json'
};

// List directory
const listResp = await fetch(`${BASE_URL}/fs/ls?path=/Users/patricksomerville/Desktop`, {
  headers
});
const files = await listResp.json();
console.log(`Found ${files.length} items`);

// Write file
const writeResp = await fetch(`${BASE_URL}/fs/write`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    path: '/Users/patricksomerville/Desktop/output.txt',
    content: 'Hello from JS!'
  })
});
const result = await writeResp.json();
console.log(result);
```

---

## Curl (Tested Working)

### Chat
```bash
curl -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a" \
     -H "Content-Type: application/json" \
     -d '{
           "model": "qwen2.5-coder:32b",
           "messages": [{"role":"user","content":"hello from local client"}]
         }' \
     https://celsa-nonsimulative-wyatt.ngrok-free.dev/v1/chat/completions
```

### Filesystem
```bash
# List directory
curl "https://celsa-nonsimulative-wyatt.ngrok-free.dev/fs/ls?path=/Users/patricksomerville/Desktop" \
  -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a"

# Read file
curl "https://celsa-nonsimulative-wyatt.ngrok-free.dev/fs/read?path=/Users/patricksomerville/Desktop/test.txt" \
  -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a"

# Write file
curl -X POST https://celsa-nonsimulative-wyatt.ngrok-free.dev/fs/write \
  -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/Users/patricksomerville/Desktop/output.txt",
    "content": "Hello from curl!"
  }'

# Execute command
curl -X POST https://celsa-nonsimulative-wyatt.ngrok-free.dev/exec \
  -H "Authorization: Bearer 90ac04027a0b4aba685dcae29eeed91a" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/Users/patricksomerville/Desktop",
    "command": ["echo", "hello"]
  }'
```

---

## LangChain

```python
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

llm = ChatOpenAI(
    model="qwen2.5-coder:32b",
    openai_api_key="90ac04027a0b4aba685dcae29eeed91a",
    openai_api_base="https://celsa-nonsimulative-wyat.ngrok-free.dev/v1",
    temperature=0.7
)

response = llm([HumanMessage(content="ping")])
print(response.content)
```

---

## Key Points

1. **API Base URL must include `/v1`** for OpenAI-compatible endpoints
2. **Token goes in Authorization header** as `Bearer <token>`
3. **Model name** is whatever's configured in Trapdoor (currently `qwen2.5-coder:32b`)
4. **Filesystem/exec tools** use the root paths (no `/v1` prefix)

---

## Common Patterns

### Agent with Tools
```python
from openai import OpenAI
import requests

class TrapdoorAgent:
    def __init__(self, base_url, token):
        self.chat = OpenAI(
            api_key=token,
            base_url=f"{base_url}/v1"
        )
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def ask(self, question):
        resp = self.chat.chat.completions.create(
            model="qwen2.5-coder:32b",
            messages=[{"role": "user", "content": question}]
        )
        return resp.choices[0].message.content

    def read_file(self, path):
        resp = requests.get(
            f"{self.base_url}/fs/read",
            params={"path": path},
            headers=self.headers
        )
        return resp.json()

    def write_file(self, path, content):
        resp = requests.post(
            f"{self.base_url}/fs/write",
            json={"path": path, "content": content},
            headers=self.headers
        )
        return resp.json()

    def run_command(self, cmd, cwd="/tmp"):
        resp = requests.post(
            f"{self.base_url}/exec",
            json={"path": cwd, "command": cmd},
            headers=self.headers
        )
        return resp.json()

# Usage
agent = TrapdoorAgent(
    "https://celsa-nonsimulative-wyatt.ngrok-free.dev",
    "90ac04027a0b4aba685dcae29eeed91a"
)

response = agent.ask("What's 2+2?")
print(response)

agent.write_file("/tmp/test.txt", "Hello!")
content = agent.read_file("/tmp/test.txt")
print(content)
```

---

**Last Updated:** 2025-10-28
**Trapdoor Version:** Enhanced Security System with multi-token support
