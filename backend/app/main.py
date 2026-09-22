"""
FastAPI entrypoint.
Wires together the API routes -> pipeline stages.

Run modes:
  - API-only (frontend served separately by `npm run dev`, port 5173):
        uvicorn app.main:app --reload
  - Merged (serves the built frontend from frontend/dist/ on the SAME
    port as the API): build the frontend first (`npm run build`), then
    run the same command above -- if frontend/dist/ exists, it's mounted
    automatically. This is what desktop_app.py uses to run the whole
    thing as one native window with no separate frontend server at all.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router

app = FastAPI(title="DepthWizard Backend")

# Allowed frontend origins. Defaults to the local Vite dev server, since
# this ships as a standalone app run on localhost -- override with a
# comma-separated CORS_ORIGINS env var if this ever needs to serve a
# frontend hosted elsewhere. Not needed at all in merged/desktop mode
# (frontend + API share an origin there), but harmless to keep enabled.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
allow_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes registered BEFORE the static mount below, so they always
# take priority -- Starlette matches routes in registration order, and
# a Mount("/") only catches paths none of the explicit routes claimed.
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the built frontend (frontend/dist/, produced by `npm run build`)
# if it exists, so the backend can act as the whole app's single entry
# point -- this is what turns it into one runnable local app instead of
# "run two dev servers and open a browser tab" during development.
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
