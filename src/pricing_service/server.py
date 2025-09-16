"""FastAPI server exposing pricing information."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
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
_last_updated: Optional[datetime] = None
_refresh_lock = asyncio.Lock()


async def _run_write_task() -> dict:
    """Run the blocking scraper pipeline in a background thread."""
    return await asyncio.to_thread(write_pricing_file, DATA_PATH)


async def _refresh_cache() -> None:
    """Populate the in-memory cache with fresh data."""
    global _cache, _last_updated
    _cache = await _run_write_task()
    _last_updated = datetime.utcnow()


async def refresh_pricing() -> None:
    """Background task to refresh pricing periodically without blocking the loop."""
    # Initial load if cache is empty
    if not _cache:
        async with _refresh_lock:
            if not _cache:
                await _refresh_cache()

    while True:
        await asyncio.sleep(REFRESH_INTERVAL)
        async with _refresh_lock:
            await _refresh_cache()


@app.on_event("startup")
async def startup_event() -> None:
    global _cache, _last_updated
    if DATA_PATH.exists():
        _cache = json.loads(DATA_PATH.read_text())
        _last_updated = datetime.utcnow()
    else:
        # Start with empty cache and refresh in background
        _cache = {}
        _last_updated = None
    # Start background tasks
    asyncio.create_task(refresh_pricing())


@app.get("/api/pricing")
async def get_pricing(
    service_type: Optional[str] = Query(None, description="Filter by service type (e.g., 'api_endpoint', 'server_rental')"),
    provider: Optional[str] = Query(None, description="Filter by provider (e.g., 'fal', 'openai', 'runway')")
) -> Dict[str, dict]:
    """Get pricing data for all models.
    
    Returns a dictionary keyed by model display name with rich metadata.
    Supports filtering by service_type and provider.
    """
    data = _cache or {}
    
    # Apply filters
    if service_type:
        data = {k: v for k, v in data.items() if v.get("service_type") == service_type}
    
    if provider:
        data = {k: v for k, v in data.items() if v.get("api_identifier") == provider}
    
    return data


@app.get("/api/pricing/{model_id}")
async def get_pricing_for_model(model_id: str) -> dict:
    """Get pricing data for a specific model by ID."""
    if not _cache:
        raise HTTPException(status_code=503, detail="Pricing cache not ready")
    model = _cache.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "updated": _last_updated.isoformat() if _last_updated else None,
        "cache_size": len(_cache) if _cache else 0
    }


@app.post("/api/refresh")
async def trigger_refresh() -> dict:
    """Trigger a background refresh of pricing data."""
    global _cache, _last_updated

    # Run refresh in background
    if _refresh_lock.locked():
        return {
            "status": "refresh_pending",
            "message": "A refresh is already running"
        }

    asyncio.create_task(_do_refresh())

    return {
        "status": "refresh_triggered",
        "message": "Pricing data refresh started in background"
    }


async def _do_refresh() -> None:
    """Internal function to perform the actual refresh."""
    async with _refresh_lock:
        try:
            await _refresh_cache()
            print(f"Pricing data refreshed successfully at {_last_updated}")
        except Exception as e:
            print(f"Failed to refresh pricing data: {e}")
