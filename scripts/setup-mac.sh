#!/bin/bash
# DayCast — Initial setup on MacBook Pro (macbook-i7)
# Run this ONCE on the target Mac to set up everything.
#
# Usage: bash scripts/setup-mac.sh
set -euo pipefail

# Ensure /usr/local/bin is in PATH (non-interactive SSH doesn't load .zshrc)
export PATH="/usr/local/bin:/usr/local/sbin:$PATH"

BREW="/usr/local/bin/brew"
PYTHON="/usr/local/bin/python3.12"
PG_BIN="/usr/local/opt/postgresql@16/bin"

DAYCAST_DIR="$HOME/daycast"
API_DIR="$DAYCAST_DIR/daycast-api"
WEB_DIR="$DAYCAST_DIR/daycast-web"
WEB_DIST="$DAYCAST_DIR/web-dist"
LOGS_DIR="$DAYCAST_DIR/logs"
BACKUPS_DIR="$DAYCAST_DIR/backups"

echo "=== DayCast Setup ==="
echo "Base directory: $DAYCAST_DIR"
echo ""

# ── 1. Create directories ──
echo "[1/9] Creating directories..."
mkdir -p "$DAYCAST_DIR" "$WEB_DIST" "$LOGS_DIR" "$BACKUPS_DIR"

# ── 2. Install system dependencies ──
echo "[2/9] Checking system dependencies..."

# Check Caddy
if ! command -v caddy &>/dev/null; then
    echo "  Caddy not found. Installing (this may take a while on Big Sur)..."
    "$BREW" install caddy || echo "  WARNING: Caddy install failed. Install manually: brew install caddy"
else
    echo "  Caddy: $(caddy version)"
fi

# Check Node.js
if ! command -v node &>/dev/null; then
    echo "  Node.js not found. Installing..."
    "$BREW" install node || echo "  WARNING: Node install failed. Install manually: brew install node"
else
    echo "  Node: $(node --version)"
fi

# ── 3. Set up PostgreSQL database ──
echo "[3/9] Setting up PostgreSQL database..."

# Ensure PostgreSQL is running
"$BREW" services start postgresql@16 2>/dev/null || true
sleep 2

# Create user and database (ignore errors if already exist)
"$PG_BIN/createuser" daycast 2>/dev/null || echo "  User 'daycast' already exists"
"$PG_BIN/createdb" -O daycast daycast 2>/dev/null || echo "  Database 'daycast' already exists"
echo "  Database ready."

# ── 4. Set up API ──
echo "[4/9] Setting up API..."
if [ ! -d "$API_DIR" ]; then
    echo "  ERROR: $API_DIR not found!"
    echo "  Please copy daycast-api to $API_DIR first (rsync or git clone)."
    exit 1
fi

cd "$API_DIR"

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "  Creating Python venv..."
    "$PYTHON" -m venv .venv
fi

echo "  Upgrading pip..."
.venv/bin/pip install --upgrade pip setuptools -q

echo "  Installing Python dependencies..."
.venv/bin/pip install . -q
echo "  Python dependencies installed."

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "  Creating .env file..."
    cat > .env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://daycast:@localhost:5432/daycast
OPENAI_API_KEY=
AUTH_MODE=none
ENVEOF
    echo "  .env created. IMPORTANT: Add your OPENAI_API_KEY to $API_DIR/.env"
else
    echo "  .env already exists."
fi

# ── 5. Run migrations ──
echo "[5/9] Running database migrations..."
cd "$API_DIR"
.venv/bin/alembic upgrade head
echo "  Migrations complete."

# ── 6. Set up Web ──
echo "[6/9] Setting up Web..."
if ! command -v node &>/dev/null; then
    echo "  SKIP: Node.js not available. Install it first: brew install node"
    echo "  Then re-run this script."
else
    if [ ! -d "$WEB_DIR" ]; then
        echo "  ERROR: $WEB_DIR not found!"
        echo "  Please copy daycast-web to $WEB_DIR first."
        exit 1
    fi

    cd "$WEB_DIR"
    echo "  Installing npm dependencies..."
    npm install 2>&1 | tail -3
    echo "  Building web..."
    npm run build 2>&1 | tail -5
    echo "  Copying build to $WEB_DIST..."
    rm -rf "$WEB_DIST"/*
    cp -R dist/* "$WEB_DIST/"
    echo "  Web build ready."
fi

# ── 7. Install Caddyfile ──
echo "[7/9] Installing Caddyfile..."
cp "$API_DIR/infra/Caddyfile" "$DAYCAST_DIR/Caddyfile"
echo "  Caddyfile installed at $DAYCAST_DIR/Caddyfile"

# ── 8. Install launchd services ──
echo "[8/9] Installing launchd services..."
LAUNCH_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_DIR"

# Make backup script executable
chmod +x "$API_DIR/infra/backup/backup.sh"

# Copy plist files
cp "$API_DIR/infra/launchd/com.daycast.api.plist" "$LAUNCH_DIR/"
cp "$API_DIR/infra/launchd/com.daycast.caddy.plist" "$LAUNCH_DIR/"
cp "$API_DIR/infra/launchd/com.daycast.backup.plist" "$LAUNCH_DIR/"

echo "  launchd plists installed."

# ── 9. Start services ──
echo "[9/9] Starting services..."

# Stop if already running (ignore errors)
launchctl unload "$LAUNCH_DIR/com.daycast.api.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_DIR/com.daycast.caddy.plist" 2>/dev/null || true

launchctl load "$LAUNCH_DIR/com.daycast.api.plist"

if command -v caddy &>/dev/null; then
    launchctl load "$LAUNCH_DIR/com.daycast.caddy.plist"
    echo "  API + Caddy started."
else
    echo "  API started. Caddy will start after installation."
fi

launchctl load "$LAUNCH_DIR/com.daycast.backup.plist" 2>/dev/null || true

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services:"
echo "  API:   http://localhost:8000/api/v1/health"
if command -v caddy &>/dev/null; then
    echo "  Web:   http://localhost (via Caddy)"
fi
echo "  LAN:   http://$(ipconfig getifaddr en0 2>/dev/null || echo '192.168.31.131')"
echo ""
echo "Next steps:"
echo "  1. Add OPENAI_API_KEY to $API_DIR/.env"
echo "  2. Test: curl http://localhost:8000/api/v1/health"
echo "  3. Open in browser from another machine"
echo ""
echo "Logs: $LOGS_DIR/"
echo "Backups: daily at 3 AM → $BACKUPS_DIR/"
