#!/bin/bash
#
# DEPLOY AND HEIST - Run this on black
#
# One command to pull the branch and execute the heist
#

set -e

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              DEPLOY AND HEIST - ONE COMMAND                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
WORKDIR="/Users/patricksomerville/Projects/Trapdoor"
BRANCH="claude/trapdoor-mesh-F705y"

cd "$WORKDIR"

echo "📍 Working directory: $WORKDIR"
echo "🌿 Target branch: $BRANCH"
echo ""

# Stash any local changes
echo "💾 Stashing local changes..."
git stash push -m "Auto-stash before heist deploy" 2>/dev/null || true

# Fetch and checkout the branch
echo "📥 Fetching branch..."
git fetch origin "$BRANCH"

echo "🔀 Checking out branch..."
git checkout "$BRANCH"

echo "📥 Pulling latest..."
git pull origin "$BRANCH"

# Verify heist script exists
if [ -f "the_heist.sh" ]; then
    echo ""
    echo "✅ the_heist.sh found!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🎬 EXECUTING THE HEIST..."
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Make it executable and run
    chmod +x the_heist.sh
    bash the_heist.sh
else
    echo ""
    echo "❌ the_heist.sh not found!"
    echo "   Listing files in $WORKDIR:"
    ls -la *.sh 2>/dev/null || echo "   No .sh files found"
    exit 1
fi
