# Qwen + Trapdoor: Local LLM with Internet Superpowers

**The Reverse Pattern:** Your local Qwen can use Trapdoor's `/exec` endpoint to reach the internet and become more capable than typical LLMs.

---

## 🌐 The Big Idea

Most local LLMs are isolated:
- ❌ Can't browse the web
- ❌ Can't make API calls
- ❌ Can't interact with online services
- ❌ Knowledge cutoff date limits them

**But with Trapdoor, Qwen can:**
- ✅ Execute commands that fetch web pages
- ✅ Call any API on the internet
- ✅ Run browser automation scripts
- ✅ Access real-time information
- ✅ Even call OTHER AI models for specialized tasks

---

## 🔧 How It Works

### The Pattern

```
User: "What's the weather in Portland?"
  ↓
Qwen thinks: "I need current data, I'll fetch it"
  ↓
Qwen (via Trapdoor): Execute curl to weather API
  ↓
Qwen gets result: {"temp": 45, "conditions": "rainy"}
  ↓
Qwen responds: "It's 45°F and rainy in Portland"
```

### The Technical Flow

1. **Chat request comes to Trapdoor**
2. **Qwen's system prompt** tells it how to use tools
3. **Qwen responds** with an action plan (fetch URL, call API, etc.)
4. **Orchestrator executes** the command via `/exec`
5. **Result goes back** to Qwen
6. **Qwen synthesizes** the final answer

---

## 💡 Capabilities Qwen Gains

### 1. Web Browsing

**Via curl/wget:**
```bash
# Qwen can instruct Trapdoor to execute:
curl -s "https://news.ycombinator.com" | grep -oP '(?<=<a href=").*?(?=")'
```

**What Qwen gets:**
- Current news headlines
- Real-time information
- Website content
- API responses

### 2. Web Scraping

**Via Python + BeautifulSoup:**
```python
# Qwen instructs Trapdoor to execute:
python3 << 'EOF'
import requests
from bs4 import BeautifulSoup

response = requests.get("https://github.com/trending")
soup = BeautifulSoup(response.text, 'html.parser')
for repo in soup.select('h2.h3 a'):
    print(repo.text.strip())
EOF
```

**What Qwen can now do:**
- Scrape GitHub trending repos
- Monitor prices on e-commerce sites
- Track social media trends
- Aggregate data from multiple sources

### 3. API Calls

**Via curl to any API:**
```bash
# Weather API
curl "https://api.weather.gov/points/45.5,-122.6" | jq '.properties.forecast'

# News API
curl "https://newsapi.org/v2/top-headlines?country=us&apiKey=$API_KEY"

# Stock prices
curl "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
```

**What Qwen gets:**
- Real-time weather
- Current news
- Stock prices
- Cryptocurrency rates
- Any public API data

### 4. Call Other AI Models

**This is the game-changer:**

```python
# Qwen instructs Trapdoor to call GPT-4 for specialized task
python3 << 'EOF'
import requests

response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
    json={
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "Analyze this code for security vulnerabilities: ..."}
        ]
    }
)
print(response.json()['choices'][0]['message']['content'])
EOF
```

**What this enables:**
- **Qwen as orchestrator:** Handles general tasks locally (free, fast)
- **GPT-4 for specialization:** Complex reasoning, security analysis
- **Claude for writing:** High-quality content generation
- **Gemini for research:** Multi-modal understanding

**You get the best of all models!**

### 5. Browser Automation

**Via Playwright/Puppeteer:**
```python
# Qwen instructs Trapdoor to run browser automation
python3 << 'EOF'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")

    # Fill forms, click buttons, extract data
    page.fill("#search", "AI tools")
    page.click("button[type=submit]")

    results = page.query_selector_all(".result")
    for result in results:
        print(result.text_content())

    browser.close()
EOF
```

**What Qwen can now do:**
- Log into websites
- Fill out forms
- Extract data from JavaScript-heavy sites
- Automate workflows
- Monitor changes on websites

### 6. Real-Time Data Processing

**Via streaming APIs:**
```python
# Qwen instructs Trapdoor to monitor live data
python3 << 'EOF'
import requests
import json

# Monitor Twitter/X stream
stream = requests.get(
    "https://api.twitter.com/2/tweets/search/stream",
    headers={"Authorization": f"Bearer {os.getenv('TWITTER_BEARER')}"},
    stream=True
)

for line in stream.iter_lines():
    if line:
        tweet = json.loads(line)
        # Qwen can analyze sentiment, extract trends, etc.
        print(f"New tweet: {tweet['data']['text']}")
EOF
```

**What Qwen can track:**
- Social media trends
- Stock market movements
- News as it breaks
- GitHub activity
- Cryptocurrency prices

### 7. File Downloads & Processing

**Via wget + processing:**
```bash
# Qwen downloads and analyzes datasets
wget -O data.csv "https://example.com/dataset.csv"
python3 -c "
import pandas as pd
df = pd.read_csv('data.csv')
print(df.describe())
print(df.groupby('category').mean())
"
```

**What Qwen can analyze:**
- CSV datasets
- JSON data dumps
- XML feeds
- Binary files (with appropriate tools)

---

## 🎯 Advanced Pattern: Multi-Model Orchestration

### Qwen as the "Brain" - Other Models as "Specialists"

```python
# System prompt for Qwen via Trapdoor:
"""
You are Qwen 2.5 Coder 32B with internet access and multi-model orchestration.

When you need specialized capabilities:
1. Security analysis → Call GPT-4 via OpenAI API
2. Creative writing → Call Claude via Anthropic API
3. Image generation → Call DALL-E or Stable Diffusion
4. Web search → Use Brave Search API or scrape Google
5. Real-time data → Call appropriate APIs (weather, stocks, news)

For general tasks, use your own capabilities (free, fast, private).
For specialized tasks, delegate to the best model for the job.

You can execute commands via the /exec endpoint to:
- curl for API calls
- python scripts for complex workflows
- browser automation for web interaction

Example workflow:
User: "Write a blog post about AI trends, include current news"
You:
1. Execute curl to fetch recent AI news
2. Analyze the news yourself
3. Call Claude API for high-quality blog writing
4. Return the final post
"""
```

### Example: Research Assistant That Actually Researches

```python
# Qwen receives: "Research the latest developments in quantum computing"

# Step 1: Qwen searches arXiv
requests.post("/exec", json={
    "cmd": ["curl", "-s", "https://export.arxiv.org/api/query?search_query=quantum+computing"]
})

# Step 2: Qwen scrapes recent papers
papers = extract_paper_titles(result)

# Step 3: For each paper, Qwen:
for paper in papers:
    # Download the PDF
    requests.post("/exec", json={
        "cmd": ["wget", paper.pdf_url]
    })

    # Extract text
    requests.post("/exec", json={
        "cmd": ["pdftotext", paper.filename]
    })

    # Analyze using GPT-4 (specialized for academic analysis)
    analysis = call_gpt4(extracted_text)

    summaries.append(analysis)

# Step 4: Qwen synthesizes everything
final_report = synthesize(summaries)
```

**Qwen now has:**
- ✅ Current research papers (via web scraping)
- ✅ Deep analysis (via GPT-4 delegation)
- ✅ Synthesis (via its own capabilities)

**All orchestrated locally, selectively calling out when needed.**

---

## 🚀 Implementing Internet Capabilities

### 1. Enhanced System Prompt

Add to Trapdoor's `DEFAULT_SYSTEM_PROMPT`:

```
You are Qwen 2.5 Coder 32B running locally with internet access capabilities.

You can access the internet by proposing HTTP calls:

TOOL: Read URL
POST /exec
{
  "cmd": ["curl", "-s", "URL_HERE"]
}

TOOL: Call API
POST /exec
{
  "cmd": ["curl", "-X", "POST", "-H", "Content-Type: application/json", "-d", "DATA", "API_URL"]
}

TOOL: Run Python Script (for complex web tasks)
POST /exec
{
  "cmd": ["python3", "-c", "PYTHON_CODE_HERE"]
}

TOOL: Browse with Playwright
POST /exec
{
  "cmd": ["python3", "/path/to/browser_script.py", "ARGUMENTS"]
}

When users ask for current information:
1. Determine what API/URL to call
2. Propose the curl/python command
3. Process the result
4. Provide the answer

Remember: All tool calls require Authorization: Bearer <token>
```

### 2. Create Helper Scripts

**`/Users/patricksomerville/Desktop/Trapdoor/tools/web_fetch.py`:**
```python
#!/usr/bin/env python3
"""
Web fetching tool for Qwen
Usage: web_fetch.py <url>
"""
import sys
import requests
from bs4 import BeautifulSoup

url = sys.argv[1]
response = requests.get(url, timeout=10)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    print(text)
else:
    print(f"Error: HTTP {response.status_code}")
    sys.exit(1)
```

**`/Users/patricksomerville/Desktop/Trapdoor/tools/api_call.py`:**
```python
#!/usr/bin/env python3
"""
Generic API caller for Qwen
Usage: api_call.py <method> <url> [json_data]
"""
import sys
import json
import requests

method = sys.argv[1]
url = sys.argv[2]
data = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None

response = requests.request(method, url, json=data, timeout=10)
print(json.dumps(response.json(), indent=2))
```

**`/Users/patricksomerville/Desktop/Trapdoor/tools/multi_model_call.py`:**
```python
#!/usr/bin/env python3
"""
Call latest frontier AI models from Qwen (2025 versions)
Usage: multi_model_call.py <model> <prompt> [reasoning_level]

Models:
  gpt5        - GPT-5 (unified reasoning, 74.9% SWE-bench, $1.25/$10 per M tokens)
  gpt5-mini   - GPT-5 Mini (faster, cheaper)
  sonnet-4.5  - Claude Sonnet 4.5 (best coding, 49% SWE-bench, $3/$15 per M tokens)
  gemini-2.5  - Gemini 2.5 Pro (1M context, 63.8% SWE-bench, thinking model)
  gemini-flash- Gemini 2.5 Flash (fast, cheap, efficient)

Reasoning levels (GPT-5 & Gemini only): minimal, low, medium, high
"""
import sys
import os
import requests
import json

if len(sys.argv) < 3:
    print("Usage: multi_model_call.py <model> <prompt> [reasoning_level]")
    sys.exit(1)

model = sys.argv[1]
prompt = sys.argv[2]
reasoning_level = sys.argv[3] if len(sys.argv) > 3 else "medium"

def call_gpt5(model_name: str, prompt: str, reasoning: str):
    """Call GPT-5 with configurable reasoning level"""
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        json={
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "reasoning_effort": reasoning  # New GPT-5 parameter
        }
    )
    result = response.json()
    # GPT-5 can show reasoning traces
    if 'reasoning' in result.get('choices', [{}])[0]:
        print("=== Reasoning Trace ===")
        print(result['choices'][0]['reasoning'])
        print("=== Final Answer ===")
    print(result['choices'][0]['message']['content'])

def call_claude_sonnet45(prompt: str):
    """Call Claude Sonnet 4.5 - best for coding and computer use"""
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.getenv('ANTHROPIC_API_KEY'),
            "anthropic-version": "2025-01-01"
        },
        json={
            "model": "claude-sonnet-4-5-20250929",  # Latest model ID
            "max_tokens": 8192,
            "thinking": {  # Extended thinking capability
                "type": "enabled",
                "budget_tokens": 10000
            },
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    result = response.json()
    # Show thinking if available
    for block in result.get('content', []):
        if block['type'] == 'thinking':
            print("=== Claude's Thinking ===")
            print(block['thinking'])
            print("=== Final Answer ===")
        elif block['type'] == 'text':
            print(block['text'])

def call_gemini25(model_name: str, prompt: str, reasoning: str):
    """Call Gemini 2.5 with thinking enabled"""
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
        headers={"x-goog-api-key": os.getenv('GOOGLE_API_KEY')},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "thinkingConfig": {  # Enable reasoning
                    "thinkingMode": reasoning  # minimal, low, medium, high
                }
            }
        }
    )
    result = response.json()
    candidate = result['candidates'][0]

    # Show thinking trace if available
    for part in candidate['content']['parts']:
        if 'thought' in part:
            print("=== Gemini's Thinking ===")
            print(part['thought'])
            print("=== Final Answer ===")
        elif 'text' in part:
            print(part['text'])

# Route to appropriate model
if model == "gpt5":
    call_gpt5("gpt-5", prompt, reasoning_level)
elif model == "gpt5-mini":
    call_gpt5("gpt-5-mini", prompt, reasoning_level)
elif model == "sonnet-4.5":
    call_claude_sonnet45(prompt)
elif model == "gemini-2.5":
    call_gemini25("gemini-2.5-pro-latest", prompt, reasoning_level)
elif model == "gemini-flash":
    call_gemini25("gemini-2.5-flash-latest", prompt, reasoning_level)
else:
    print(f"Unknown model: {model}")
    print("Available: gpt5, gpt5-mini, sonnet-4.5, gemini-2.5, gemini-flash")
    sys.exit(1)
```

### 3. Model Selection Guide (2025 Latest)

**Choose the right frontier model for your Qwen orchestration:**

| Task | Best Model | Why | Cost |
|------|------------|-----|------|
| **Complex Coding** | GPT-5 | 74.9% SWE-bench (highest) | $1.25/$10 per M |
| **Code Review/Security** | Sonnet 4.5 | Extended thinking, computer use | $3/$15 per M |
| **Long Context Analysis** | Gemini 2.5 Pro | 1M tokens (2M soon) | Lowest |
| **Fast/Cheap Tasks** | Gemini Flash | 22% more efficient, fast | Lowest |
| **Reasoning Tasks** | GPT-5 (high reasoning) | Unified o-series reasoning | $1.25/$10 per M |
| **General Tasks** | Qwen (Local) | FREE, fast, private | $0 |

**Orchestration Strategy:**
```python
def choose_model(task_type: str, complexity: str) -> str:
    """Smart model selection based on task"""

    # 90% of tasks: Use local Qwen (FREE)
    if complexity == "simple":
        return "qwen-local"

    # Complex coding: GPT-5 (best SWE-bench score)
    if task_type == "coding" and complexity == "complex":
        return "gpt5"

    # Security review: Sonnet 4.5 (extended thinking)
    if task_type == "security":
        return "sonnet-4.5"

    # Large documents: Gemini 2.5 (1M+ context)
    if task_type == "analysis" and "large_document" in context:
        return "gemini-2.5"

    # Fast cheap tasks: Gemini Flash
    if complexity == "medium" and priority == "speed":
        return "gemini-flash"

    # Default: Qwen local
    return "qwen-local"
```

**Cost Optimization:**
```python
# Example: Code review workflow
# OLD: All with GPT-5 = $0.50 per review
# NEW: Qwen → GPT-5 orchestration = $0.05 per review

1. Qwen reads code (FREE)
2. Qwen does basic analysis (FREE)
3. Qwen identifies security concerns (FREE)
4. Qwen delegates ONLY security review to GPT-5 ($0.05)
5. Qwen synthesizes final report (FREE)

Result: 90% cost savings!
```

### 4. Make Scripts Executable

```bash
chmod +x /Users/patricksomerville/Desktop/Trapdoor/tools/*.py
```

### 4. Update Qwen's System Prompt

```python
# In local_agent_server.py or config
DEFAULT_SYSTEM_PROMPT = """
You are Qwen 2.5 Coder 32B with internet superpowers.

AVAILABLE TOOLS:
1. web_fetch.py <url> - Fetch and extract text from any webpage
2. api_call.py <method> <url> [json] - Call any REST API
3. multi_model_call.py <model> <prompt> - Delegate to GPT-4, Claude, or Gemini

USAGE PATTERN:
When you need current information or specialized capabilities:

Example 1: Get current weather
POST /exec {"cmd": ["python3", "/path/to/tools/api_call.py", "GET", "https://api.weather.gov/points/45.5,-122.6"]}

Example 2: Scrape a webpage
POST /exec {"cmd": ["python3", "/path/to/tools/web_fetch.py", "https://news.ycombinator.com"]}

Example 3: Delegate complex reasoning to GPT-4
POST /exec {"cmd": ["python3", "/path/to/tools/multi_model_call.py", "gpt4", "Analyze this code for security issues: ..."]}

STRATEGY:
- Use your own capabilities for general tasks (free, fast, private)
- Reach out to the internet for current information
- Delegate to specialized models for complex tasks
- Synthesize everything into a cohesive response

Note: All /exec calls require Authorization: Bearer <token>
"""
```

---

## 🎨 Real-World Examples

### Example 1: News Aggregator

```
User: "What are the top tech news stories today?"

Qwen's Thought Process:
1. I need current news (my training data is old)
2. I'll fetch from multiple sources
3. I'll synthesize a summary

Qwen executes:
- curl https://news.ycombinator.com (HN headlines)
- curl https://www.reddit.com/r/technology/.json (Reddit)
- curl https://techcrunch.com (TechCrunch)

Qwen processes results:
- Extracts headlines
- Identifies common themes
- Ranks by relevance

Qwen responds:
"Here are today's top tech stories:
1. OpenAI releases GPT-5 (trending on HN, Reddit, TC)
2. Apple announces new Vision Pro 2 (TechCrunch)
3. ..."
```

### Example 2: Stock Analysis with Multi-Model Orchestration

```
User: "Should I invest in NVDA?"

Qwen's Strategy:
1. Get current stock data (I'll fetch from Yahoo Finance)
2. Get recent news (I'll scrape financial sites)
3. Deep analysis (I'll delegate to GPT-4)
4. Synthesis (I'll do this myself)

Qwen executes:
POST /exec {"cmd": ["curl", "https://query1.finance.yahoo.com/v8/finance/chart/NVDA"]}
→ Gets current price, historical data

POST /exec {"cmd": ["python3", "web_fetch.py", "https://finance.yahoo.com/quote/NVDA/news"]}
→ Gets recent news headlines

POST /exec {"cmd": ["python3", "multi_model_call.py", "gpt4", "Analyze NVDA: Current price $500, up 200% YoY, PE ratio 65, news: ..."]}
→ GPT-4 does deep financial analysis

Qwen synthesizes:
"Based on current data and analysis:
- Current price: $500 (up 200% this year)
- GPT-4 analysis suggests: [detailed analysis]
- My recommendation: [synthesis]
- Risk factors: [list]
- Consider: [alternatives]"
```

### Example 3: Research Paper Summary

```
User: "Summarize the latest paper on quantum error correction"

Qwen's Process:
1. Search arXiv for recent papers
2. Download the top result
3. Extract text from PDF
4. Call Claude for academic summarization
5. Present the summary

Qwen executes:
POST /exec {"cmd": ["curl", "https://export.arxiv.org/api/query?search_query=quantum+error+correction"]}
→ Finds paper: "Novel QEC Codes" (arXiv:2024.12345)

POST /exec {"cmd": ["wget", "https://arxiv.org/pdf/2024.12345.pdf"]}
→ Downloads PDF

POST /exec {"cmd": ["pdftotext", "2024.12345.pdf"]}
→ Extracts text

POST /exec {"cmd": ["python3", "multi_model_call.py", "claude", "Summarize this quantum computing paper: [text]"]}
→ Claude provides expert summary

Qwen presents:
"Latest paper on quantum error correction:
Title: Novel QEC Codes
Authors: [list]
Key findings: [Claude's summary]
Implications: [my analysis]
"
```

---

## 🔐 Security Considerations

### Rate Limiting

Add to your system prompt:
```
RATE LIMITS:
- Web requests: Max 10/minute
- API calls to paid services: Max 5/minute
- Model delegations: Max 3/minute (these cost money!)

Always check if information is REALLY needed before calling external services.
```

### Cost Management

```python
# Track API usage
API_COSTS = {
    "gpt4": 0.03,  # per 1K tokens
    "claude": 0.024,
    "gemini": 0.001
}

# Add to system prompt:
"""
COST AWARENESS:
Before delegating to paid models, consider:
1. Can I handle this myself? (free)
2. Is this a specialized task that needs GPT-4/Claude?
3. Have I already used my budget today?

Delegation hierarchy (cheapest to most expensive):
1. Self (Qwen) - FREE
2. Gemini - $0.001/1K tokens
3. Claude - $0.024/1K tokens
4. GPT-4 - $0.03/1K tokens

Only delegate when specialized capability is truly needed.
"""
```

---

## 📊 Performance Comparison

### Traditional Local LLM
```
Query: "What's the weather today?"
Response: "I don't have access to current weather data. My training data is from..."
Result: ❌ Unhelpful
```

### Qwen + Trapdoor Internet Access
```
Query: "What's the weather today?"
Qwen: [executes curl to weather API]
Qwen: [processes JSON response]
Response: "It's currently 45°F and rainy in Portland."
Result: ✅ Helpful, current, accurate
```

### Traditional Local LLM + Specialized Task
```
Query: "Review this code for security vulnerabilities"
Response: [Qwen does its best, might miss subtle issues]
Result: ⚠️ Good but not expert-level
```

### Qwen + Multi-Model Orchestration
```
Query: "Review this code for security vulnerabilities"
Qwen: "This requires security expertise, delegating to GPT-4"
Qwen: [calls GPT-4 via API]
GPT-4: [expert security analysis]
Qwen: [synthesizes and presents findings]
Result: ✅ Expert-level analysis at fraction of full GPT-4 cost
```

---

## 🎯 Implementation Checklist

### Week 1: Basic Internet Access
- [ ] Create `tools/` directory
- [ ] Add `web_fetch.py` script
- [ ] Add `api_call.py` script
- [ ] Update Qwen's system prompt
- [ ] Test web scraping
- [ ] Test API calls

### Week 2: Multi-Model Orchestration
- [ ] Add `multi_model_call.py` script
- [ ] Set up API keys (OpenAI, Anthropic, Google)
- [ ] Test model delegation
- [ ] Add cost tracking
- [ ] Create usage dashboard

### Week 3: Advanced Capabilities
- [ ] Browser automation setup (Playwright)
- [ ] Real-time data streaming
- [ ] Scheduled tasks (via cron + Trapdoor)
- [ ] Build custom tools library

---

## 🚀 The Vision

**Qwen becomes a "Universal Agent Orchestrator":**

```
                    ┌─────────────┐
                    │    Qwen     │
                    │  (Local)    │
                    │  Free, Fast │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
      ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
      │  Internet │  │ GPT-4   │  │  Claude   │
      │   APIs    │  │ (Paid)  │  │  (Paid)   │
      └───────────┘  └─────────┘  └───────────┘
            │              │              │
      Weather, News,   Security,      Writing,
      Stocks, Data     Reasoning      Quality
```

**You get:**
- ✅ Local intelligence (Qwen) for 90% of tasks
- ✅ Internet access for current information
- ✅ Specialist models for complex domains
- ✅ Best of all worlds at minimal cost

---

**This is the future: Local orchestrators calling cloud specialists.**

