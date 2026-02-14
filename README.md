# DayCast API

Backend for DayCast — a personal AI-powered service that transforms daily inputs (text, links, photos) into tailored content for multiple channels (blog, diary, Telegram, Twitter/X).

Built with Python 3.12, FastAPI, SQLAlchemy 2.0, and PostgreSQL.

## Features

- **Input items** — CRUD for text, URLs, and images. URLs are auto-extracted via trafilatura. Images stored on disk. Star importance rating (1–5). Include/exclude from AI generation toggle.
- **AI generation** — sends all day's inputs to OpenAI GPT-5.2 and produces formatted text per channel. Custom AI instructions and business/personal separation via generation settings.
- **5 channels** — Blog, Diary, Telegram Personal, Telegram Public, Twitter/X. Each with configurable style, language, and length.
- **10 styles** — concise, detailed, structured, plan, advisory, casual, funny, serious, list_numbered, list_bulleted.
- **5 lengths** — brief, short, medium, detailed, full.
- **4 languages** — Russian, English, German, Armenian.
- **Generation settings** — per-user custom AI instruction and separate business/personal toggle.
- **History** — browse past days, search by text, view all inputs and generations.
- **Soft-delete** — deleted/cleared items stay in history, not sent to AI.
- **Edit history** — old versions preserved on edit, viewable in history.
- **Export day** — export all day's items as plain text with timestamps.
- **Rate limiting** — 10 AI generations/day, 120 API requests/min.
- **User authentication** — register/login with username + password. Passwords hashed with bcrypt. JWT tokens (30-day expiry) sent as `Authorization: Bearer`. Each user sees only their own data.
- **Publishing** — publish generation results or raw input items to the public blog. Slug-based URLs. Unpublish at any time. Batch status check for UI.
- **Public API** — unauthenticated endpoints for the public blog site: post feed with cursor pagination and filters, single post by slug, calendar heatmap, monthly archive, site stats, RSS feed. Supports both generation-based and input-based posts.
- **Static web serving** — serves the built React SPA alongside the API.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/auth/register` | Register (username + password → JWT) |
| `POST` | `/api/v1/auth/login` | Login (username + password → JWT) |
| `POST` | `/api/v1/inputs` | Add input item (text/url/image) |
| `GET` | `/api/v1/inputs?date=YYYY-MM-DD` | List items for a date |
| `GET` | `/api/v1/inputs/{id}` | Get single item |
| `PUT` | `/api/v1/inputs/{id}` | Edit item (content, importance, include_in_generation) |
| `DELETE` | `/api/v1/inputs/{id}` | Soft-delete item |
| `GET` | `/api/v1/inputs/export?date=&format=` | Export day as plain text |
| `DELETE` | `/api/v1/inputs?date=YYYY-MM-DD` | Clear day (soft-delete) |
| `GET` | `/api/v1/uploads/{path}` | Serve uploaded image |
| `POST` | `/api/v1/generate` | Generate content for all active channels |
| `POST` | `/api/v1/generate/{id}/regenerate` | Regenerate for specific channels |
| `GET` | `/api/v1/days` | List days (cursor, limit, search) |
| `GET` | `/api/v1/days/{date}` | Day detail (items + generations) |
| `DELETE` | `/api/v1/days/{date}` | Delete entire day |
| `GET` | `/api/v1/channels` | List available channels |
| `GET` | `/api/v1/styles` | List available styles |
| `GET` | `/api/v1/languages` | List available languages |
| `GET` | `/api/v1/lengths` | List available lengths |
| `GET` | `/api/v1/settings/channels` | Get channel settings |
| `POST` | `/api/v1/settings/channels` | Save channel settings |
| `GET` | `/api/v1/settings/generation` | Get generation settings |
| `POST` | `/api/v1/settings/generation` | Save generation settings |
| `POST` | `/api/v1/publish` | Publish a generation result |
| `POST` | `/api/v1/publish/input` | Publish an input item directly |
| `DELETE` | `/api/v1/publish/{id}` | Unpublish a post |
| `GET` | `/api/v1/publish/status` | Batch check publish status (generation results) |
| `GET` | `/api/v1/publish/input-status` | Batch check publish status (input items) |
| `GET` | `/api/v1/public/posts` | Public post feed (cursor, channel, language, date filters) |
| `GET` | `/api/v1/public/posts/{slug}` | Single public post by slug |
| `GET` | `/api/v1/public/calendar` | Calendar heatmap (year, month) |
| `GET` | `/api/v1/public/archive` | Monthly archive with post counts |
| `GET` | `/api/v1/public/stats` | Site statistics |
| `GET` | `/api/v1/public/rss` | RSS 2.0 feed |

## Tech Stack

- **Python 3.12** + **FastAPI**
- **SQLAlchemy 2.0** (async) + **Alembic** migrations
- **PostgreSQL 16** (via Homebrew on production Mac)
- **OpenAI GPT-5.1** for content generation
- **trafilatura** for URL text extraction
- **bcrypt** for password hashing
- **PyJWT** for JWT token creation/verification
- **structlog** for structured JSON logging

## Project Structure

```
daycast-api/
├── app/
│   ├── main.py              # FastAPI app, routers, SPA serving
│   ├── config.py            # Settings (from .env)
│   ├── database.py          # SQLAlchemy async engine
│   ├── dependencies.py      # Request dependencies (client_id, db)
│   ├── errors.py            # Unified error handling
│   ├── rate_limit.py        # Rate limiting
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response DTOs
│   ├── routers/             # API endpoint handlers
│   └── services/            # Business logic (AI, URL extraction, file storage)
├── alembic/                 # Database migrations (001–007)
├── config/product.yml       # Channels, styles, languages, lengths, limits, AI config
├── prompts/                 # AI prompt templates (generate, regenerate)
├── infra/                   # Caddyfile, launchd plists, backup scripts
├── scripts/                 # setup-mac.sh, deploy.sh
├── tests/                   # pytest tests
├── docs/                    # deploy.md, changelog.md
├── docker-compose.yml       # PostgreSQL for local development
├── Makefile                 # dev, test, lint, migrate, deploy-mac
├── pyproject.toml
└── .env.example
```

## Database Schema

8 migrations applied:
1. **001** — Initial schema: `clients`, `input_items`, `generations`, `generation_results`, `channel_settings`
2. **002** — Add `extracted_text` to `input_items` (for URL content)
3. **003** — Add `cleared` flag to `input_items` (soft-delete)
4. **004** — Add `input_item_edits` table (edit history)
5. **005** — Add `default_length` to `channel_settings`
6. **006** — Add `users` table (authentication)
7. **007** — Add `published_posts` table (publishing)
8. **008** — Add `importance`, `include_in_generation` to `input_items`; create `generation_settings` table; add `input_item_id`, `text` to `published_posts`

## Setup (Local Development)

```bash
# Create venv and install
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start PostgreSQL (Docker)
docker compose up -d

# Configure
cp .env.example .env
# Edit .env — set OPENAI_API_KEY

# Run migrations
make migrate

# Start dev server
make dev
```

## Setup (Production — Mac)

See [docs/deploy.md](docs/deploy.md) for full instructions. In short:

```bash
# From dev machine — deploy to Mac
make deploy-mac
```

The production Mac (192.168.31.131) runs everything natively — no Docker:
- PostgreSQL 16 via Homebrew
- Python 3.12 venv with uvicorn
- Static web files served by the API directly
- launchd for auto-start, daily backups at 3 AM

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start dev server on port 8000 |
| `make test` | Run pytest |
| `make lint` | Check code with ruff |
| `make migrate` | Apply Alembic migrations |
| `make deploy-mac` | Deploy to production Mac via rsync + SSH |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://daycast:daycast@localhost:5432/daycast` |
| `OPENAI_API_KEY` | OpenAI API key (required for generation) | — |
| `JWT_SECRET` | Secret key for JWT signing (required) | `change-me-in-production` |
| `AUTH_MODE` | Authentication mode (legacy, unused) | `none` |

## License

Private project.
