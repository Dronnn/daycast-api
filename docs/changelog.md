# Changelog

## Step 11 — Flame Rating & Default Importance (2026-02-12)

- **Default importance = 5**: new inputs now default to importance 5 (maximum) instead of 0/null. Ensures every item starts at highest priority.
- **Flame rating replaces stars**: star rating UI replaced with progressive-size flame icons (5 levels). Web uses flame icons in Feed. iOS uses `FlameRatingView` (replaces `StarRatingView`).
- **iOS: flames on image items**: flame rating now visible on image input items too (previously only shown on text/URL items).

## Step 10 — Batch 2: Input Control, Generation Settings, Direct Publishing (2026-02-11)

- **Input importance**: 1–5 star rating on input items (`importance` column). Filter/prioritize items for generation.
- **Include/exclude from generation**: `include_in_generation` boolean flag on input items. Excluded items are skipped by AI generation but remain visible in feed.
- **Generation settings**: new `generation_settings` table (per-client). Custom AI instruction text and "separate business & personal" toggle. Settings passed to AI prompts during generation.
- **Publish input items directly**: publish raw input items (not just generation results) to the public blog. New endpoint `POST /publish/input`, `GET /publish/input-status`. Published input posts have `source: "input"`, nullable `channel_id`/`style`/`language`.
- **Export day**: `GET /inputs/export?date=YYYY-MM-DD&format=plain` — export all day's items as plain text with timestamps.
- **New styles**: `list_numbered` and `list_bulleted` added to style options.
- **Updated input CRUD**: `PUT /inputs/{id}` now supports partial updates (importance, include_in_generation without changing content). Edit history only saved when content actually changes.
- **Generation settings endpoints**: `GET /settings/generation`, `POST /settings/generation`.
- **Migration 008**: adds `importance`, `include_in_generation` to `input_items`; creates `generation_settings` table; adds `input_item_id`, `text` to `published_posts`; makes `generation_result_id` nullable.
- **Importance passed to AI**: items with star rating now include `[importance: N/5]` in the AI prompt. Prompt instructs the model to give higher-importance items more weight and prominence.
- **Deploy fix**: added `venv` to rsync exclude list to prevent wiping production virtualenv.
- **Public API updates**: public post responses now include `source` field; input-based posts served correctly.

## Step 9 — Publishing & Public API (2026-02-10)

- **Published posts model**: `published_posts` table (id UUID, generation_result_id FK, client_id FK, slug UNIQUE, published_at). Migration 007 with DESC index on `published_at`.
- **Publish router** (`app/routers/publish.py`): `POST /publish` (publish a result, generates slug), `DELETE /publish/{id}` (unpublish), `GET /publish/status?result_ids=...` (batch status check).
- **Public router** (`app/routers/public.py`): unauthenticated endpoints for the public blog site:
  - `GET /public/posts` — cursor-paginated feed with channel, language, date filters.
  - `GET /public/posts/{slug}` — single post by slug with input previews.
  - `GET /public/calendar?year=&month=` — calendar heatmap (dates with post counts).
  - `GET /public/archive` — monthly archive with post counts and labels.
  - `GET /public/stats` — total posts, total days, channels used.
  - `GET /public/rss` — RSS 2.0 XML feed (last 50 posts).
- **Archive fix**: fixed `get_archive` query — use `select_from(PublishedPost)` to fix missing FROM clause, generate month labels via Python `calendar` module instead of PostgreSQL `to_char(Month)`.
- **Image generation fix**: images were sent to OpenAI as relative file paths, causing `AI provider error`. Now reads image files from disk, encodes as base64 data URLs (`data:image/jpeg;base64,...`) before sending to OpenAI Vision API.
- Deployed: migration 007 applied, API restarted.

## Step 8 — User Authentication (2026-02-10)

- **User model**: `users` table (id UUID PK, username UNIQUE, password_hash, created_at). Migration 006.
- **Auth service** (`app/services/auth.py`): bcrypt password hashing, JWT creation/verification (HS256, 30-day expiry).
- **Auth endpoints**: `POST /api/v1/auth/register` (creates user + client, returns JWT), `POST /api/v1/auth/login` (validates credentials, returns JWT).
- **Protected endpoints**: `app/dependencies.py` rewritten — extracts `user_id` from JWT `Authorization: Bearer` header, uses as `client_id`. All existing endpoints unchanged. No token → 401.
- **Health endpoint** remains public (no auth required).
- **Dependencies**: added `bcrypt>=4.0`, `pyjwt>=2.8` to `pyproject.toml`.
- **Config**: added `JWT_SECRET` setting to `app/config.py` and `.env.example`.
- **Error handling**: added 409 (conflict) code for duplicate username registration.
- Deployed on production Mac: `pip install bcrypt pyjwt`, `JWT_SECRET` set in `.env`, migration 006 applied, API restarted.

## Step 7 — Full Feature Set (2026-02-10)

- **Length control**: added `default_length` to channel settings (migration 005). 5 options: brief, short, medium, detailed, full. Length passed to AI prompt. New endpoint `GET /lengths`. UI selector in Channels page.
- Updated `product.yml` — added `lengths` section.
- Updated `generate_v1.md` — AI prompt now includes length instructions.
- Copy button fix on Generate page (HTTP fallback via `document.execCommand`).

## Step 6 — Soft-Delete, Edit History, Copy Fix (2026-02-10)

- **Soft-delete for individual messages**: `DELETE /inputs/{id}` sets `cleared=True` instead of removing from DB. Deleted items visible in History with "Deleted" badge.
- **Filtered generation**: `POST /generate` and regenerate endpoints filter out `cleared=True` items — deleted/cleared items don't go to AI.
- **Edit history**: new `input_item_edits` table (migration 004). `PUT /inputs/{id}` saves old content before updating. History detail shows edit history per item.
- **Copy button fix**: added `document.execCommand('copy')` fallback for HTTP (non-HTTPS) contexts. Copy works on all pages.
- Badges in History: "Deleted" for soft-deleted, "Edited" for modified items, "Show edit history" button.

## Step 5 — Soft-Delete, History, Channels (2026-02-10)

- **OPENAI_API_KEY** configured on production Mac.
- **AI model**: changed from `gpt-5.2` to `gpt-5.1` (5.2 not available).
- **API parameter**: `max_tokens` → `max_completion_tokens` (gpt-5.1 format).
- **Single client_id**: all devices use fixed UUID `00000000-0000-4000-a000-000000000001`. Changed `app/dependencies.py`. Existing data migrated.
- **Soft-delete for Clear Day**: added `cleared` field to `input_items` (migration 003). Clear day sets `cleared=True`. Feed shows only non-cleared. History shows everything.
- **History page**: rewritten — loads real data from `GET /days`, search works.
- **History detail page**: new route `/history/:date` — shows all items (with "Cleared" badge) and all generations with Copy.
- **Channels page**: rewritten — loads/saves settings via API, Save button, controlled state.

## Steps 2–4 — CRUD, Images, URLs, AI Generation (2026-02-09 – 2026-02-10)

- SQLAlchemy models: `clients`, `input_items`, `generations`, `generation_results`, `channel_settings`.
- Alembic migrations 001–002.
- Full CRUD for input items (text, URL, image).
- Image upload to disk (`data/uploads/`), served via `/api/v1/uploads/`.
- URL text extraction via trafilatura (stored in `extracted_text` field).
- AI generation module (`app/services/ai.py`): collects day's inputs, builds prompt, calls OpenAI, parses JSON response, retries on failure.
- Prompt templates: `generate_v1.md`, `regenerate_v1.md`.
- Regenerate endpoint (per-channel or all).
- Days endpoints: list, detail, delete.
- Catalog endpoints: channels, styles, languages.
- Channel settings endpoints: get/save.
- Unified error handling (`ErrorResponse`).
- Rate limiting (10 AI/day, 120 req/min).
- Tests with pytest.

## Step 1 — Backend Skeleton (2026-02-09)

- Project structure created (`app/`, `tests/`, `config/`, `docs/`, `prompts/`, `infra/`)
- FastAPI app with CORS middleware
- Health endpoint: `GET /api/v1/health`
- SQLAlchemy async engine + session factory
- Alembic configured for async PostgreSQL migrations
- Docker Compose for PostgreSQL 15
- Product config (`config/product.yml`): channels, styles, languages, limits
- Makefile with `dev`, `test`, `lint`, `migrate` targets
- pytest test for health endpoint

## Infrastructure (2026-02-10)

- `infra/Caddyfile` — reverse proxy config
- `infra/launchd/` — plist files for API, Caddy, backup auto-start
- `infra/backup/backup.sh` — pg_dump + 7-day rotation
- `scripts/setup-mac.sh` — first-time Mac setup
- `scripts/deploy.sh` — deploy via rsync + SSH
- `docs/deploy.md` — deployment documentation
- Makefile `deploy-mac` target
