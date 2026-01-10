#!/bin/bash
#
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                           THE HEIST                                        ║
# ║                   Ocean's Eleven Style Orchestration                       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# Assembling the crew:
#   - Claude Code agents (The Specialists)
#   - Gemini CLI (The Analyst)
#   - Aider (The Surgeon)
#   - Qwen 32B (The Local Genius)
#   - Multiple machines (The Network)
#
# Run this on black: bash the_heist.sh

set -e

# Configuration
WORKDIR="/Users/patricksomerville/Projects/Trapdoor"
RESULTS_DIR="$WORKDIR/heist_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Colors for style
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║${NC}                           ${YELLOW}T H E   H E I S T${NC}                              ${PURPLE}║${NC}"
echo -e "${PURPLE}║${NC}                    ${CYAN}Multi-Agent Parallel Orchestration${NC}                    ${PURPLE}║${NC}"
echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Mission:${NC} Get the entire memory stack operational"
echo -e "${YELLOW}Target:${NC} Workday + Memory Bridge + Supermemory + Total Capture + Qdrant"
echo -e "${YELLOW}Results:${NC} $RESULTS_DIR"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}                         ASSEMBLING THE CREW${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ============================================================================
# DANNY OCEAN - Claude Code Lead (Orchestration)
# ============================================================================
echo -e "${GREEN}🎩 Danny Ocean${NC} - Claude Code Lead"
echo "   Task: Coordinate the integration, ensure all pieces connect"
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model sonnet --prompt "
You are Danny Ocean - the lead orchestrator.

Your job is to review all the pieces and create the master integration plan:

1. Read these files and understand the architecture:
   - memory_bridge.py (Qdrant)
   - supermemory_bridge.py (Cloud memory)
   - conductor_endpoints.py (GET endpoints)
   - total_capture.py (Capture daemon)
   - hangar.py (Fleet spawning)

2. Create a file called INTEGRATION_MANIFEST.md that documents:
   - What each component does
   - How they connect
   - The order of operations to get everything working
   - Any missing pieces

3. Identify the critical path - what MUST work first

Be concise but thorough. This is the master plan.
" > "$RESULTS_DIR/01_danny_ocean_manifest.md" 2>&1
) &
PID_DANNY=$!
echo "   Started: PID $PID_DANNY"

# ============================================================================
# RUSTY RYAN - Claude Code (Memory Stack)
# ============================================================================
echo -e "${GREEN}🃏 Rusty Ryan${NC} - Claude Code (Memory Stack)"
echo "   Task: Get all memory systems connected and tested"
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are Rusty Ryan - the right hand, memory specialist.

Your mission: Get the memory stack operational.

1. Check Qdrant status: curl -s http://localhost:6333/health || echo 'Qdrant not running'

2. If Qdrant is down, start it:
   docker run -d -p 6333:6333 -p 6334:6334 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant

3. Configure Supermemory API key:
   mkdir -p ~/.trapdoor
   echo '{\"api_key\": \"sm_Mh7Whw6BFuwrxqS5y4KVcA_oYFuPGbTEWvrXDlbuumTtYOHasNEfMGXZqcFNXxJdnSwSvpBkxhWULxMDjfpHhNY\"}' > ~/.trapdoor/supermemory.json

4. Test both:
   python3 memory_bridge.py health
   python3 supermemory_bridge.py health

5. Add test memories to both:
   python3 memory_bridge.py store 'Heist memory test - local Qdrant' --source heist
   python3 supermemory_bridge.py add 'Heist memory test - cloud Supermemory' --source heist

6. Verify search works on both

Report status of each step.
" > "$RESULTS_DIR/02_rusty_memory.md" 2>&1
) &
PID_RUSTY=$!
echo "   Started: PID $PID_RUSTY"

# ============================================================================
# LINUS CALDWELL - Claude Code (Workday Finish)
# ============================================================================
echo -e "${GREEN}🎭 Linus Caldwell${NC} - Claude Code (Workday)"
echo "   Task: Finish the Workday app"
(
    cd /Users/patricksomerville/Workday/backend
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are Linus Caldwell - the new guy proving himself.

Your mission: Finish the Workday productivity tracker.

1. Read server.js thoroughly
2. Fix any bugs or incomplete code
3. Add a test mode that simulates keystrokes for testing
4. Make sure sessions save correctly to workday-sessions/
5. Test the full flow: start -> wait 10 seconds -> stop -> check saved file

The app should:
- Track session duration
- Calculate productivity score
- Save to JSON + gzip
- Work with PostgreSQL if available, local-only otherwise

Report what you fixed and prove it works.
" > "$RESULTS_DIR/03_linus_workday.md" 2>&1
) &
PID_LINUS=$!
echo "   Started: PID $PID_LINUS"

# ============================================================================
# BASHER TARR - Claude Code (Total Capture)
# ============================================================================
echo -e "${GREEN}💣 Basher Tarr${NC} - Claude Code (Total Capture)"
echo "   Task: Get Total Capture running and verified"
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are Basher Tarr - the explosives expert (but for data capture).

Your mission: Get Total Capture fully operational.

1. Review total_capture.py
2. Run the daemon for 30 seconds: timeout 30 python3 total_capture.py daemon &
3. While it runs, do some things to capture:
   - Copy something to clipboard
   - Switch between apps
   - Maybe touch a file
4. Check stats: python3 total_capture.py stats
5. Search for what was captured: python3 total_capture.py recent

Report how many events were captured and from which sources.
" > "$RESULTS_DIR/04_basher_capture.md" 2>&1
) &
PID_BASHER=$!
echo "   Started: PID $PID_BASHER"

# ============================================================================
# LIVINGSTON DELL - Gemini CLI (Analysis)
# ============================================================================
echo -e "${BLUE}📡 Livingston Dell${NC} - Gemini (Analysis)"
echo "   Task: Analyze the codebase and find integration points"
(
    cd "$WORKDIR"
    # Check if gemini CLI is available
    if command -v gemini &> /dev/null; then
        gemini --prompt "
Analyze these Python files and explain how they should work together:
- memory_bridge.py: $(head -50 memory_bridge.py)
- supermemory_bridge.py: $(head -50 supermemory_bridge.py)
- total_capture.py: $(head -50 total_capture.py)

Suggest the optimal integration architecture.
" > "$RESULTS_DIR/05_livingston_gemini.md" 2>&1
    else
        echo "Gemini CLI not available - using Qwen as backup" > "$RESULTS_DIR/05_livingston_gemini.md"
        curl -s http://localhost:11434/api/generate -d '{
            "model": "qwen2.5-coder:32b",
            "prompt": "Analyze the trapdoor memory architecture: memory_bridge.py connects to Qdrant, supermemory_bridge.py connects to cloud, total_capture.py captures events. How should these integrate? Be concise.",
            "stream": false
        }' | jq -r '.response' >> "$RESULTS_DIR/05_livingston_gemini.md" 2>&1
    fi
) &
PID_LIVINGSTON=$!
echo "   Started: PID $PID_LIVINGSTON"

# ============================================================================
# TURK MALLOY - Aider (Code Surgery)
# ============================================================================
echo -e "${PURPLE}🔧 Turk Malloy${NC} - Aider (Code Surgery)"
echo "   Task: Integrate routers into local_agent_server.py"
(
    cd "$WORKDIR"
    if command -v aider &> /dev/null; then
        aider --yes --no-git --message "
Add these imports at the top of local_agent_server.py:
from memory_bridge import create_memory_router
from supermemory_bridge import create_supermemory_router
from conductor_endpoints import create_conductor_router

Then add these lines after the app is created:
app.include_router(create_memory_router(), prefix='/v1/memory')
app.include_router(create_supermemory_router(), prefix='/v1/supermemory')
app.include_router(create_conductor_router(), prefix='/conductor')

Make the minimal changes needed.
" local_agent_server.py > "$RESULTS_DIR/06_turk_aider.md" 2>&1
    else
        echo "Aider not available - manual integration needed" > "$RESULTS_DIR/06_turk_aider.md"
        echo "" >> "$RESULTS_DIR/06_turk_aider.md"
        echo "Add to local_agent_server.py:" >> "$RESULTS_DIR/06_turk_aider.md"
        echo "from memory_bridge import create_memory_router" >> "$RESULTS_DIR/06_turk_aider.md"
        echo "from supermemory_bridge import create_supermemory_router" >> "$RESULTS_DIR/06_turk_aider.md"
        echo "from conductor_endpoints import create_conductor_router" >> "$RESULTS_DIR/06_turk_aider.md"
        echo "app.include_router(create_memory_router(), prefix='/v1/memory')" >> "$RESULTS_DIR/06_turk_aider.md"
        echo "app.include_router(create_supermemory_router(), prefix='/v1/supermemory')" >> "$RESULTS_DIR/06_turk_aider.md"
        echo "app.include_router(create_conductor_router(), prefix='/conductor')" >> "$RESULTS_DIR/06_turk_aider.md"
    fi
) &
PID_TURK=$!
echo "   Started: PID $PID_TURK"

# ============================================================================
# VIRGIL MALLOY - Qwen 32B (Local Intelligence)
# ============================================================================
echo -e "${CYAN}🧠 Virgil Malloy${NC} - Qwen 32B (Local Intelligence)"
echo "   Task: Design the churning/sorting layer"
(
    curl -s http://localhost:11434/api/generate -d '{
        "model": "qwen2.5-coder:32b",
        "prompt": "Design a Python module called pattern_engine.py that:\n1. Reads captured events from SQLite (total_capture events)\n2. Identifies patterns (repeated commands, common workflows, time-based patterns)\n3. Generates insights like:\n   - \"You often run git commit after pytest - consider a pre-commit hook\"\n   - \"Your productivity peaks at 10am - schedule deep work then\"\n4. Updates a patterns.json file with extracted patterns\n5. Can generate suggestions for tomorrow based on today patterns\n\nProvide the complete Python implementation. Be thorough but practical.",
        "stream": false,
        "options": {"num_predict": 4000}
    }' | jq -r '.response' > "$RESULTS_DIR/07_virgil_qwen.md" 2>&1
) &
PID_VIRGIL=$!
echo "   Started: PID $PID_VIRGIL"

# ============================================================================
# SAUL BLOOM - Claude Code (Documentation)
# ============================================================================
echo -e "${YELLOW}📜 Saul Bloom${NC} - Claude Code (Documentation)"
echo "   Task: Update CLAUDE.md with new capabilities"
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are Saul Bloom - the elder statesman, keeper of wisdom.

Your mission: Update CLAUDE.md to document all new capabilities.

Add a new section covering:
1. Memory Stack (Qdrant, Supermemory, Milvus)
2. Total Capture system
3. Conductor pattern (spawning agents via WebFetch)
4. The Hangar (fleet spawning)
5. Workday integration

Keep the existing content, just add the new sections.
Make it practical - show exact commands to use each feature.
" > "$RESULTS_DIR/08_saul_docs.md" 2>&1
) &
PID_SAUL=$!
echo "   Started: PID $PID_SAUL"

# ============================================================================
# REUBEN TISHKOFF - Claude on nvidia-spark (GPU Check)
# ============================================================================
echo -e "${RED}💰 Reuben Tishkoff${NC} - Claude on nvidia-spark (GPU Status)"
echo "   Task: Check GPU resources and model availability"
(
    ssh nvidia-spark "
        echo '=== GPU STATUS ==='
        nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv 2>/dev/null || echo 'nvidia-smi not available'
        echo ''
        echo '=== OLLAMA MODELS ==='
        ollama list 2>/dev/null || echo 'ollama not running'
        echo ''
        echo '=== DISK SPACE ==='
        df -h / | tail -1
    " > "$RESULTS_DIR/09_reuben_gpu.md" 2>&1 || echo "Could not reach nvidia-spark" > "$RESULTS_DIR/09_reuben_gpu.md"
) &
PID_REUBEN=$!
echo "   Started: PID $PID_REUBEN"

# ============================================================================
# YEN - Claude on silver-fox (Storage Check)
# ============================================================================
echo -e "${GREEN}🤸 Yen${NC} - Claude on silver-fox (Storage Status)"
echo "   Task: Check storage and sync status"
(
    ssh silver-fox "
        echo '=== STORAGE STATUS ==='
        df -h / | tail -1
        echo ''
        echo '=== TRAPDOOR STATUS ==='
        curl -s http://localhost:8080/health 2>/dev/null || echo 'trapdoor not running'
        echo ''
        echo '=== RECENT FILES ==='
        ls -lt ~/Desktop/*.md 2>/dev/null | head -5 || echo 'No recent md files'
    " > "$RESULTS_DIR/10_yen_storage.md" 2>&1 || echo "Could not reach silver-fox" > "$RESULTS_DIR/10_yen_storage.md"
) &
PID_YEN=$!
echo "   Started: PID $PID_YEN"

# ============================================================================
# FRANK CATTON - Claude (Terminal Boss Check)
# ============================================================================
echo -e "${PURPLE}🎲 Frank Catton${NC} - Claude Code (Terminal Boss)"
echo "   Task: Verify Terminal Boss is capturing commands"
(
    cd "$WORKDIR/terminal_boss"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are Frank Catton - the inside man.

Your mission: Verify Terminal Boss is capturing terminal commands.

1. Check if terminal_boss.py is running: ps aux | grep terminal_boss
2. Check the SQLite database for recent entries
3. If not running, check what's needed to start it
4. Run: python3 terminal_boss.py stats
5. Verify Milvus sync is configured

Report the capture status.
" > "$RESULTS_DIR/11_frank_terminalboss.md" 2>&1
) &
PID_FRANK=$!
echo "   Started: PID $PID_FRANK"

# ============================================================================
# Wait for the crew
# ============================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}                           THE HEIST IN PROGRESS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "⏳ All agents deployed. Waiting for completion..."
echo ""

# Track completion
TOTAL=11
COMPLETED=0
FAILED=0

wait_agent() {
    local pid=$1
    local name=$2
    if wait $pid 2>/dev/null; then
        echo -e "   ${GREEN}✓${NC} $name complete"
        ((COMPLETED++))
    else
        echo -e "   ${RED}✗${NC} $name failed"
        ((FAILED++))
    fi
}

wait_agent $PID_DANNY "Danny Ocean"
wait_agent $PID_RUSTY "Rusty Ryan"
wait_agent $PID_LINUS "Linus Caldwell"
wait_agent $PID_BASHER "Basher Tarr"
wait_agent $PID_LIVINGSTON "Livingston Dell"
wait_agent $PID_TURK "Turk Malloy"
wait_agent $PID_VIRGIL "Virgil Malloy"
wait_agent $PID_SAUL "Saul Bloom"
wait_agent $PID_REUBEN "Reuben Tishkoff"
wait_agent $PID_YEN "Yen"
wait_agent $PID_FRANK "Frank Catton"

# ============================================================================
# The Debrief
# ============================================================================
echo ""
echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║${NC}                           ${GREEN}THE DEBRIEF${NC}                                    ${PURPLE}║${NC}"
echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   ${GREEN}Completed:${NC} $COMPLETED / $TOTAL"
echo -e "   ${RED}Failed:${NC} $FAILED / $TOTAL"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Show summaries
for f in "$RESULTS_DIR"/*.md; do
    echo -e "${YELLOW}━━━ $(basename $f) ━━━${NC}"
    head -30 "$f"
    echo ""
done

echo ""
echo -e "${GREEN}Full results:${NC} $RESULTS_DIR"
echo ""
echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║${NC}                        ${YELLOW}THE HEIST IS COMPLETE${NC}                            ${PURPLE}║${NC}"
echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
