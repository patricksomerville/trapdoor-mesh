#!/bin/bash
#
# ORCHESTRATE NOW - Spawn parallel Claude Code agents
#
# Run this on black to spawn multiple Claude agents working in parallel
# Each agent reports back through the mesh
#
# Usage: bash orchestrate_now.sh

set -e

WORKDIR="/Users/patricksomerville/Projects/Trapdoor"
RESULTS_DIR="$WORKDIR/orchestration_results"
mkdir -p "$RESULTS_DIR"

echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║              CONDUCTOR - PARALLEL ORCHESTRATION                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Spawning Claude Code agents in parallel..."
echo "Results will be saved to: $RESULTS_DIR"
echo ""

# ============================================================================
# AGENT 1: Finish Workday Backend
# ============================================================================
echo "🚀 Agent 1: Finishing Workday backend..."
(
    cd /Users/patricksomerville/Workday/backend
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are finishing the Workday productivity tracking app.

Current state:
- server.js exists with basic structure
- PostgreSQL connection to Neon configured
- WebSocket server on port 3001
- workday-sessions directory exists but empty

Your tasks:
1. Review server.js and fix any issues
2. Add proper keystroke simulation for testing (since real keystroke capture needs accessibility)
3. Make sure the session saving to workday-sessions/ works
4. Test the start/stop/status commands
5. Create a simple test that proves sessions are being saved

Output a summary of what you fixed and what's now working.
" > "$RESULTS_DIR/agent1_workday.md" 2>&1
) &
PID1=$!

# ============================================================================
# AGENT 2: Integrate Memory Stack
# ============================================================================
echo "🚀 Agent 2: Integrating memory stack into trapdoor..."
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are integrating the memory stack into the trapdoor server.

Files to work with:
- local_agent_server.py (main trapdoor server)
- memory_bridge.py (Qdrant integration - in repo)
- supermemory_bridge.py (Supermemory integration - in repo)
- conductor_endpoints.py (GET endpoints for spawning - in repo)

Your tasks:
1. Read the current local_agent_server.py
2. Add imports for the three bridge modules
3. Add the routers:
   - app.include_router(create_memory_router(), prefix='/v1/memory')
   - app.include_router(create_supermemory_router(), prefix='/v1/supermemory')
   - app.include_router(create_conductor_router(), prefix='/conductor')
4. Test that the server still starts

Output the exact changes you made.
" > "$RESULTS_DIR/agent2_memory_integration.md" 2>&1
) &
PID2=$!

# ============================================================================
# AGENT 3: Configure Supermemory
# ============================================================================
echo "🚀 Agent 3: Configuring Supermemory..."
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are configuring Supermemory for the trapdoor mesh.

API Key: sm_Mh7Whw6BFuwrxqS5y4KVcA_oYFuPGbTEWvrXDlbuumTtYOHasNEfMGXZqcFNXxJdnSwSvpBkxhWULxMDjfpHhNY

Your tasks:
1. Create ~/.trapdoor/supermemory.json with the API key
2. Test the connection by running: python3 supermemory_bridge.py health
3. If it works, add a test memory: python3 supermemory_bridge.py add 'Test memory from orchestration'
4. Search to verify: python3 supermemory_bridge.py search 'test'

Output the results of each step.
" > "$RESULTS_DIR/agent3_supermemory.md" 2>&1
) &
PID3=$!

# ============================================================================
# AGENT 4: Set up Total Capture
# ============================================================================
echo "🚀 Agent 4: Setting up Total Capture daemon..."
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are setting up the Total Capture system.

File: total_capture.py (in the repo)

Your tasks:
1. Review total_capture.py and understand the agents
2. Run: python3 total_capture.py status (check current state)
3. Test a quick capture: python3 total_capture.py daemon &
4. Let it run for 30 seconds, then check: python3 total_capture.py stats
5. Document what was captured

Output what's working and what needs adjustment.
" > "$RESULTS_DIR/agent4_total_capture.md" 2>&1
) &
PID4=$!

# ============================================================================
# AGENT 5: Verify Qdrant/Cipher
# ============================================================================
echo "🚀 Agent 5: Verifying Qdrant/Cipher setup..."
(
    cd "$WORKDIR"
    claude --print --dangerously-skip-permissions --model haiku --prompt "
You are verifying the Qdrant vector database setup.

Expected: Qdrant running in Docker at localhost:6333

Your tasks:
1. Check if Qdrant is running: curl http://localhost:6333/health
2. If not running, start it: docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
3. Test memory_bridge.py: python3 memory_bridge.py health
4. If working, add a test: python3 memory_bridge.py store 'Test from orchestration' --category knowledge
5. Search to verify: python3 memory_bridge.py search 'orchestration'

Output the status of each step.
" > "$RESULTS_DIR/agent5_qdrant.md" 2>&1
) &
PID5=$!

# ============================================================================
# Wait for all agents
# ============================================================================
echo ""
echo "⏳ Waiting for all agents to complete..."
echo "   Agent 1 (Workday): PID $PID1"
echo "   Agent 2 (Memory Integration): PID $PID2"
echo "   Agent 3 (Supermemory): PID $PID3"
echo "   Agent 4 (Total Capture): PID $PID4"
echo "   Agent 5 (Qdrant): PID $PID5"
echo ""

wait $PID1 && echo "✓ Agent 1 complete" || echo "✗ Agent 1 failed"
wait $PID2 && echo "✓ Agent 2 complete" || echo "✗ Agent 2 failed"
wait $PID3 && echo "✓ Agent 3 complete" || echo "✗ Agent 3 failed"
wait $PID4 && echo "✓ Agent 4 complete" || echo "✗ Agent 4 failed"
wait $PID5 && echo "✓ Agent 5 complete" || echo "✗ Agent 5 failed"

# ============================================================================
# Collect results
# ============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                         RESULTS SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

for f in "$RESULTS_DIR"/*.md; do
    echo "━━━ $(basename $f) ━━━"
    head -50 "$f"
    echo ""
done

echo ""
echo "Full results saved to: $RESULTS_DIR"
echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                    ORCHESTRATION COMPLETE                         ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
