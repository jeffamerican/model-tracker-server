"""FastAPI server exposing pricing information."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from .scraper import write_pricing_file

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "model_pricing.json"
REFRESH_INTERVAL = 6 * 60 * 60  # 6 hours

app = FastAPI(title="Pricing Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static UI
app.mount(
    "/ui",
    StaticFiles(directory=Path(__file__).resolve().parents[2] / "ui", html=True),
    name="ui",
)


@app.get("/")
async def root() -> RedirectResponse:
    """Redirect to UI."""
    return RedirectResponse(url="/ui/")

_cache: Dict[str, dict] | None = None


async def refresh_pricing() -> None:
    """Background task to refresh pricing periodically."""
    global _cache
    while True:
        _cache = write_pricing_file(DATA_PATH)
        await asyncio.sleep(REFRESH_INTERVAL)


@app.on_event("startup")
async def startup_event() -> None:
    global _cache
    if DATA_PATH.exists():
        _cache = json.loads(DATA_PATH.read_text())
    else:
        _cache = write_pricing_file(DATA_PATH)
    asyncio.create_task(refresh_pricing())


@app.get("/api/pricing")
async def get_pricing() -> Dict[str, dict]:
    return _cache or {}


@app.get("/api/pricing/{model_id}")
async def get_pricing_for_model(model_id: str) -> dict:
    if not _cache:
        raise HTTPException(status_code=503, detail="Pricing cache not ready")
    model = _cache.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model
