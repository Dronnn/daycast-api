# DayCast — Deploy to Mac

Target: MacBook Pro Mid 2014, macOS Big Sur, `192.168.31.131`

## Architecture

```
Browser (new Mac) ──→ http://192.168.31.131
                           │
                         Caddy (:80)
                        /         \
              /api/*              /*
                │                  │
           uvicorn (:8000)    static files
           (FastAPI)          (Vite build)
                │
           PostgreSQL (:5432)
```

## Prerequisites (already installed)

- Homebrew
- Python 3.12
- PostgreSQL 16 (via `brew services`)

## First-time setup

### 1. Copy code to the Mac

From your development machine:

```bash
ssh macbook-i7 "mkdir -p ~/daycast"

rsync -az --exclude '.venv' --exclude 'data/' --exclude '__pycache__' \
    daycast-api/ macbook-i7:~/daycast/daycast-api/

rsync -az --exclude 'node_modules' --exclude 'dist' \
    daycast-web/ macbook-i7:~/daycast/daycast-web/
```

### 2. Run setup on the Mac

```bash
ssh macbook-i7
cd ~/daycast/daycast-api
bash scripts/setup-mac.sh
```

This will:
- Install Caddy and Node.js via Homebrew
- Create PostgreSQL database (`daycast`)
- Create Python venv and install dependencies
- Run database migrations
- Build web (npm install + vite build)
- Install Caddyfile and launchd services
- Start API + Caddy

### 3. Add OpenAI API key

```bash
ssh macbook-i7
nano ~/daycast/daycast-api/.env
# Set: OPENAI_API_KEY=sk-...
```

### 4. Test

From your development machine:

```bash
# Health check
curl http://192.168.31.131/api/v1/health

# Open web UI
open http://192.168.31.131
```

## Subsequent deploys

From the project root on your dev machine:

```bash
# From daycast/ root:
bash daycast-api/scripts/deploy.sh

# Or from daycast-api/:
make deploy-mac
```

This will rsync code, rebuild web, run migrations, and restart services.

## Managing services

SSH to the Mac first: `ssh macbook-i7`

```bash
# Check service status
launchctl list | grep daycast

# Restart API
launchctl unload ~/Library/LaunchAgents/com.daycast.api.plist
launchctl load ~/Library/LaunchAgents/com.daycast.api.plist

# Restart Caddy
launchctl unload ~/Library/LaunchAgents/com.daycast.caddy.plist
launchctl load ~/Library/LaunchAgents/com.daycast.caddy.plist

# Stop everything
launchctl unload ~/Library/LaunchAgents/com.daycast.api.plist
launchctl unload ~/Library/LaunchAgents/com.daycast.caddy.plist
```

## Logs

```bash
# API
tail -f ~/daycast/logs/api-stderr.log

# Caddy
tail -f ~/daycast/logs/caddy-stderr.log

# Caddy access
tail -f ~/daycast/logs/caddy-access.log
```

## Backups

Automated daily at 3:00 AM via launchd.

```bash
# Manual backup
bash ~/daycast/daycast-api/infra/backup/backup.sh

# List backups
ls -la ~/daycast/backups/

# Restore
gunzip -c ~/daycast/backups/daycast_YYYYMMDD_HHMMSS.sql.gz | \
    /usr/local/opt/postgresql@16/bin/psql daycast
```

## Directory structure on Mac

```
~/daycast/
├── daycast-api/       # API source + .venv + .env
│   └── data/uploads/  # Uploaded images (persisted)
├── daycast-web/       # Web source (for building)
├── web-dist/          # Built static files (served by Caddy)
├── Caddyfile          # Active Caddy config
├── logs/              # All service logs
└── backups/           # Daily pg_dump files
```

## Troubleshooting

**API not responding:**
```bash
ssh macbook-i7
cat ~/daycast/logs/api-stderr.log
# Check if .env exists and DATABASE_URL is correct
```

**Caddy not starting:**
```bash
ssh macbook-i7
caddy validate --config ~/daycast/Caddyfile
cat ~/daycast/logs/caddy-stderr.log
```

**Database connection error:**
```bash
ssh macbook-i7
brew services list | grep postgresql
/usr/local/opt/postgresql@16/bin/psql -l  # list databases
```
