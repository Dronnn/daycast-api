#!/bin/bash
# DayCast — Deploy from dev machine to Mac
# Run this from your development machine to push code and restart services.
#
# Usage: bash scripts/deploy.sh
set -euo pipefail

MAC_HOST="macbook-i7"
MAC_USER="andrewmaier"
REMOTE_DIR="/Users/$MAC_USER/daycast"
LOCAL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=== DayCast Deploy ==="
echo "Source: $LOCAL_ROOT"
echo "Target: $MAC_HOST:$REMOTE_DIR"
echo ""

# ── 1. Sync API code ──
echo "[1/5] Syncing API code..."
rsync -az --delete \
    --exclude '.venv' \
    --exclude '.env' \
    --exclude 'data/' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    --exclude '.ruff_cache' \
    "$LOCAL_ROOT/daycast-api/" \
    "$MAC_HOST:$REMOTE_DIR/daycast-api/"
echo "  API synced."

# ── 2. Sync Web code ──
echo "[2/5] Syncing Web code..."
rsync -az --delete \
    --exclude 'node_modules' \
    --exclude 'dist' \
    "$LOCAL_ROOT/daycast-web/" \
    "$MAC_HOST:$REMOTE_DIR/daycast-web/"
echo "  Web synced."

# ── 3. Remote: install deps + migrate + build ──
echo "[3/5] Installing dependencies & running migrations..."
ssh "$MAC_HOST" << 'REMOTE_SCRIPT'
set -euo pipefail
cd ~/daycast/daycast-api

# Update Python deps
.venv/bin/pip install -e ".[dev]" -q 2>&1 | tail -1

# Run migrations
.venv/bin/alembic upgrade head

echo "  API deps & migrations done."
REMOTE_SCRIPT

echo "[4/5] Building web..."
ssh "$MAC_HOST" << 'REMOTE_SCRIPT'
set -euo pipefail
cd ~/daycast/daycast-web

npm install --silent
npm run build

# Copy build output
rm -rf ~/daycast/web-dist/*
cp -R dist/* ~/daycast/web-dist/
echo "  Web build done."
REMOTE_SCRIPT

# ── 5. Restart services ──
echo "[5/5] Restarting services..."
ssh "$MAC_HOST" << 'REMOTE_SCRIPT'
set -euo pipefail
LAUNCH_DIR="$HOME/Library/LaunchAgents"

# Update Caddyfile
cp ~/daycast/daycast-api/infra/Caddyfile ~/daycast/Caddyfile

# Update launchd plists
cp ~/daycast/daycast-api/infra/launchd/com.daycast.api.plist "$LAUNCH_DIR/"
cp ~/daycast/daycast-api/infra/launchd/com.daycast.caddy.plist "$LAUNCH_DIR/"
cp ~/daycast/daycast-api/infra/launchd/com.daycast.backup.plist "$LAUNCH_DIR/"
chmod +x ~/daycast/daycast-api/infra/backup/backup.sh

# Restart API
launchctl unload "$LAUNCH_DIR/com.daycast.api.plist" 2>/dev/null || true
launchctl load "$LAUNCH_DIR/com.daycast.api.plist"

# Restart Caddy
launchctl unload "$LAUNCH_DIR/com.daycast.caddy.plist" 2>/dev/null || true
launchctl load "$LAUNCH_DIR/com.daycast.caddy.plist"

echo "  Services restarted."
REMOTE_SCRIPT

echo ""
echo "=== Deploy Complete ==="
echo ""

# Health check
echo "Health check..."
sleep 2
if ssh "$MAC_HOST" "curl -sf http://localhost/api/v1/health" > /dev/null 2>&1; then
    echo "  API is UP"
else
    echo "  API might still be starting — check logs on Mac"
fi
echo ""
echo "Open: http://192.168.31.131"
