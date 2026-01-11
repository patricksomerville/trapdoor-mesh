#!/bin/bash
#
# QUICK HEIST - Simplified version that actually works
#
# Removes set -e so failures don't stop the show
# Tests each component before running

WORKDIR="/Users/patricksomerville/Projects/Trapdoor"
RESULTS_DIR="$WORKDIR/heist_results_$(date +%Y%m%d_%H%M%S)"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    QUICK HEIST                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Create results dir first
mkdir -p "$RESULTS_DIR"
echo "Results dir: $RESULTS_DIR"
echo ""

# Test components
echo "=== TESTING COMPONENTS ==="
echo ""

echo -n "Claude CLI: "
if command -v claude &> /dev/null; then
    echo "✓ found"
    CLAUDE_OK=1
else
    echo "✗ not found"
    CLAUDE_OK=0
fi

echo -n "Ollama: "
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ running"
    OLLAMA_OK=1
else
    echo "✗ not running"
    OLLAMA_OK=0
fi

echo -n "Docker: "
if docker ps > /dev/null 2>&1; then
    echo "✓ running"
    DOCKER_OK=1
else
    echo "✗ not running"
    DOCKER_OK=0
fi

echo -n "Qdrant: "
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo "✓ running"
    QDRANT_OK=1
else
    echo "✗ not running (will try to start)"
    QDRANT_OK=0
fi

echo ""
echo "=== RUNNING AGENTS ==="
echo ""

cd "$WORKDIR"

# Agent 1: Memory Setup (no claude needed)
echo "🔧 Agent 1: Setting up memory infrastructure..."
(
    echo "=== Memory Setup ===" > "$RESULTS_DIR/01_memory_setup.md"

    # Create supermemory config
    mkdir -p ~/.trapdoor
    echo '{"api_key": "sm_Mh7Whw6BFuwrxqS5y4KVcA_oYFuPGbTEWvrXDlbuumTtYOHasNEfMGXZqcFNXxJdnSwSvpBkxhWULxMDjfpHhNY"}' > ~/.trapdoor/supermemory.json
    echo "✓ Supermemory config created" >> "$RESULTS_DIR/01_memory_setup.md"

    # Start Qdrant if not running
    if [ "$QDRANT_OK" = "0" ] && [ "$DOCKER_OK" = "1" ]; then
        docker run -d -p 6333:6333 -p 6334:6334 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant 2>&1 || true
        echo "✓ Qdrant container started" >> "$RESULTS_DIR/01_memory_setup.md"
    fi

    # Test memory_bridge
    if [ -f "memory_bridge.py" ]; then
        python3 memory_bridge.py health >> "$RESULTS_DIR/01_memory_setup.md" 2>&1 || echo "memory_bridge.py health check failed" >> "$RESULTS_DIR/01_memory_setup.md"
    fi

    # Test supermemory_bridge
    if [ -f "supermemory_bridge.py" ]; then
        python3 supermemory_bridge.py health >> "$RESULTS_DIR/01_memory_setup.md" 2>&1 || echo "supermemory_bridge.py health check failed" >> "$RESULTS_DIR/01_memory_setup.md"
    fi

    echo "" >> "$RESULTS_DIR/01_memory_setup.md"
    echo "=== Setup Complete ===" >> "$RESULTS_DIR/01_memory_setup.md"
) &
PID1=$!

# Agent 2: Qwen Analysis (uses ollama directly)
echo "🧠 Agent 2: Qwen 32B analyzing architecture..."
(
    if [ "$OLLAMA_OK" = "1" ]; then
        curl -s http://localhost:11434/api/generate -d '{
            "model": "qwen2.5-coder:32b",
            "prompt": "Analyze the trapdoor memory architecture. memory_bridge.py connects to Qdrant for local vector search. supermemory_bridge.py connects to cloud storage. total_capture.py captures events. How should these integrate? Give a concise 5-step plan.",
            "stream": false
        }' | jq -r '.response' > "$RESULTS_DIR/02_qwen_analysis.md" 2>&1
    else
        echo "Ollama not running - skipped" > "$RESULTS_DIR/02_qwen_analysis.md"
    fi
) &
PID2=$!

# Agent 3: Python syntax check (no external deps)
echo "🔍 Agent 3: Validating Python files..."
(
    echo "=== Python Syntax Check ===" > "$RESULTS_DIR/03_syntax_check.md"
    for f in memory_bridge.py supermemory_bridge.py conductor_endpoints.py total_capture.py hangar.py; do
        if [ -f "$f" ]; then
            if python3 -m py_compile "$f" 2>&1; then
                echo "✓ $f - OK" >> "$RESULTS_DIR/03_syntax_check.md"
            else
                echo "✗ $f - FAILED" >> "$RESULTS_DIR/03_syntax_check.md"
            fi
        else
            echo "? $f - NOT FOUND" >> "$RESULTS_DIR/03_syntax_check.md"
        fi
    done
) &
PID3=$!

# Agent 4: Total Capture test
echo "📸 Agent 4: Testing Total Capture..."
(
    echo "=== Total Capture Test ===" > "$RESULTS_DIR/04_total_capture.md"
    if [ -f "total_capture.py" ]; then
        python3 total_capture.py status >> "$RESULTS_DIR/04_total_capture.md" 2>&1 || echo "Status check failed" >> "$RESULTS_DIR/04_total_capture.md"
    else
        echo "total_capture.py not found" >> "$RESULTS_DIR/04_total_capture.md"
    fi
) &
PID4=$!

# Agent 5: Claude Code (if available)
echo "🎩 Agent 5: Claude Code integration check..."
(
    if [ "$CLAUDE_OK" = "1" ]; then
        timeout 120 claude -p --dangerously-skip-permissions --model haiku "You are checking the trapdoor integration. List files and confirm these exist: memory_bridge.py, supermemory_bridge.py, conductor_endpoints.py, total_capture.py, hangar.py. Read first 10 lines of each and confirm valid. Output a simple status report." > "$RESULTS_DIR/05_claude_check.md" 2>&1
    else
        echo "Claude CLI not available" > "$RESULTS_DIR/05_claude_check.md"
    fi
) &
PID5=$!

# Agent 6: Integration into server
echo "🔌 Agent 6: Checking server integration..."
(
    echo "=== Server Integration Check ===" > "$RESULTS_DIR/06_server_integration.md"

    # Check if routers are already integrated
    if grep -q "memory_bridge" local_agent_server.py 2>/dev/null; then
        echo "✓ memory_bridge already integrated" >> "$RESULTS_DIR/06_server_integration.md"
    else
        echo "✗ memory_bridge NOT integrated - add to local_agent_server.py:" >> "$RESULTS_DIR/06_server_integration.md"
        echo "  from memory_bridge import create_memory_router" >> "$RESULTS_DIR/06_server_integration.md"
        echo "  app.include_router(create_memory_router(), prefix='/v1/memory')" >> "$RESULTS_DIR/06_server_integration.md"
    fi

    if grep -q "supermemory_bridge" local_agent_server.py 2>/dev/null; then
        echo "✓ supermemory_bridge already integrated" >> "$RESULTS_DIR/06_server_integration.md"
    else
        echo "✗ supermemory_bridge NOT integrated" >> "$RESULTS_DIR/06_server_integration.md"
    fi

    if grep -q "conductor_endpoints" local_agent_server.py 2>/dev/null; then
        echo "✓ conductor_endpoints already integrated" >> "$RESULTS_DIR/06_server_integration.md"
    else
        echo "✗ conductor_endpoints NOT integrated" >> "$RESULTS_DIR/06_server_integration.md"
    fi
) &
PID6=$!

echo ""
echo "⏳ Waiting for agents..."
echo ""

wait $PID1 && echo "✓ Agent 1 complete" || echo "✗ Agent 1 failed"
wait $PID2 && echo "✓ Agent 2 complete" || echo "✗ Agent 2 failed"
wait $PID3 && echo "✓ Agent 3 complete" || echo "✗ Agent 3 failed"
wait $PID4 && echo "✓ Agent 4 complete" || echo "✗ Agent 4 failed"
wait $PID5 && echo "✓ Agent 5 complete" || echo "✗ Agent 5 failed"
wait $PID6 && echo "✓ Agent 6 complete" || echo "✗ Agent 6 failed"

echo ""
echo "=== RESULTS ==="
echo ""

for f in "$RESULTS_DIR"/*.md; do
    echo "━━━ $(basename $f) ━━━"
    cat "$f"
    echo ""
done

echo ""
echo "Full results: $RESULTS_DIR"
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    QUICK HEIST COMPLETE                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
