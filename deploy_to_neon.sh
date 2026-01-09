#!/bin/bash
# Deploy trapdoor hub to Neon mothership

set -e

NEON="patrick@100.80.193.92"
NEON_DIR="/data/trapdoor-hub"

echo "╔════════════════════════════════════════╗"
echo "║  Deploying trapdoor hub to Neon       ║"
echo "╚════════════════════════════════════════╝"
echo

# 1. Create directory on Neon
echo "1. Creating directory on Neon..."
ssh $NEON "mkdir -p $NEON_DIR"

# 2. Copy files
echo "2. Copying files..."
scp hub_server.py $NEON:$NEON_DIR/
scp terminal_client.py $NEON:$NEON_DIR/

# 3. Create requirements.txt
echo "3. Creating requirements.txt..."
cat > /tmp/requirements.txt << 'EOF'
fastapi==0.104.1
websockets==12.0
uvicorn==0.24.0
pymilvus==2.3.0
requests==2.31.0
EOF
scp /tmp/requirements.txt $NEON:$NEON_DIR/

# 4. Create docker-compose entry
echo "4. Creating docker-compose configuration..."
cat > /tmp/trapdoor-compose.yml << 'EOF'
  trapdoor-hub:
    image: python:3.12-slim
    container_name: trapdoor-hub
    restart: unless-stopped
    working_dir: /app
    volumes:
      - /data/trapdoor-hub:/app
    ports:
      - "8081:8081"
    command: >
      bash -c "pip install -q -r requirements.txt &&
               python hub_server.py 8081"
    networks:
      - somertime
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    environment:
      - PYTHONUNBUFFERED=1
EOF

echo
echo "Docker compose entry created at /tmp/trapdoor-compose.yml"
echo
echo "5. Next steps (run on Neon):"
echo "   ssh $NEON"
echo "   cd /data"
echo "   # Add contents of /tmp/trapdoor-compose.yml to docker-compose.yml"
echo "   docker-compose up -d trapdoor-hub"
echo "   docker logs -f trapdoor-hub"
echo

# 5. Test connection
echo "6. Testing connection..."
if ssh $NEON "curl -sf http://localhost:8081/health" > /dev/null 2>&1; then
    echo "   ✓ Hub is accessible from Neon"
else
    echo "   Note: Hub needs to be started with docker-compose first"
fi

echo
echo "╔════════════════════════════════════════╗"
echo "║  Deployment preparation complete       ║"
echo "╚════════════════════════════════════════╝"
