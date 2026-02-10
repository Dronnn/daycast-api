import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.errors import AppError, app_error_handler, http_exception_handler
from app.routers import auth, catalog, days, generate, health, inputs, public, publish, settings, uploads

app = FastAPI(title="DayCast API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(inputs.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(generate.router, prefix="/api/v1")
app.include_router(days.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(publish.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")

# Serve static web files (replaces Caddy on Big Sur)
WEB_DIST = Path(os.environ.get("WEB_DIST_DIR", Path.home() / "daycast" / "web-dist"))
if WEB_DIST.is_dir() and (WEB_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = WEB_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEB_DIST / "index.html")
