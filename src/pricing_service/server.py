"""FastAPI server exposing pricing information."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
import httpx

from .scraper import write_pricing_file, incremental_update_pricing_file

try:  # Optional import to enrich fal.ai schemas when dependencies are present
    from .scrapers import fal as fal_scraper
except Exception:  # pragma: no cover - scraping deps missing at runtime
    fal_scraper = None

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

# Serve thumbnails and assets (only if directory exists)
assets_path = Path(__file__).resolve().parents[2] / "assets"
if assets_path.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=assets_path, html=False),
        name="assets",
    )


@app.get("/")
async def root() -> RedirectResponse:
    """Redirect to UI."""
    return RedirectResponse(url="/ui/")

_cache: Dict[str, dict] | None = None
_last_updated: Optional[datetime] = None
_last_change_summary: Optional[dict] = None
_refresh_lock = asyncio.Lock()


def _normalize_model_id(model_id: str | None) -> str | None:
    """Collapse duplicated provider prefixes within a model identifier."""
    if not model_id:
        return model_id
    parts = [part for part in model_id.split("/") if part]
    if len(parts) >= 2 and parts[0].lower() == parts[1].lower():
        parts = [parts[0]] + parts[2:]
    return "/".join(parts)


def _normalize_cache(data: Dict[str, dict]) -> Dict[str, dict]:
    """Ensure api_schema entries are JSON objects when possible."""
    normalized_data: Dict[str, dict] = {}
    for key, record in data.items():
        schema = record.get("api_schema")
        if isinstance(schema, str):
            text = schema.strip()
            if not text:
                record["api_schema"] = None
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            else:
                record["api_schema"] = parsed
                schema = record["api_schema"]

        # Enrich fal.ai schema payloads with parameter metadata when possible
        if (
            fal_scraper
            and record.get("api_identifier") == "fal"
            and schema
        ):
            normalized_schema = fal_scraper._normalize_api_schema_payload(schema)
            if normalized_schema:
                base = fal_scraper._generate_api_schema(
                    record.get("model_id", ""),
                    record.get("unit", "") or record.get("service_type", "")
                )
                record["api_schema"] = fal_scraper._merge_json_schemas(base, normalized_schema)
        normalized_model_id = _normalize_model_id(record.get("model_id") or key)
        if normalized_model_id:
            record["model_id"] = normalized_model_id

        raw_payload = record.get("raw")
        if isinstance(raw_payload, dict):
            raw_endpoint = raw_payload.get("endpoint")
            normalized_endpoint = _normalize_model_id(raw_endpoint)
            if normalized_endpoint:
                raw_payload["endpoint"] = normalized_endpoint

        normalized_key = _normalize_model_id(key) or key
        normalized_data[normalized_key] = record

    return normalized_data


async def _run_incremental_update_task() -> tuple[dict, dict]:
    """Run the incremental update pipeline in a background thread."""
    return await asyncio.to_thread(incremental_update_pricing_file, DATA_PATH)


async def _run_write_task() -> dict:
    """Run the blocking scraper pipeline in a background thread (legacy method)."""
    return await asyncio.to_thread(write_pricing_file, DATA_PATH)


async def _refresh_cache() -> None:
    """Populate the in-memory cache with fresh data using incremental updates."""
    global _cache, _last_updated, _last_change_summary
    updated_data, change_summary = await _run_incremental_update_task()
    _cache = _normalize_cache(updated_data)
    _last_updated = datetime.utcnow()
    _last_change_summary = change_summary


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
        print(f"📊 Loading pricing data from {DATA_PATH}")
        _cache = _normalize_cache(json.loads(DATA_PATH.read_text()))
        _last_updated = datetime.utcnow()
        print(f"✅ Loaded {len(_cache)} pricing records")
    else:
        # Start with empty cache and refresh in background
        print("⚠️  No existing pricing data found. Initializing scrapers...")
        print("   First request may take 30-60 seconds while data is collected.")
        _cache = {}
        _last_updated = None
    # Start background tasks
    asyncio.create_task(refresh_pricing())
    print("🚀 Pricing Service started and ready to serve requests")


def _get_filtered_data(
    service_type: Optional[str] = None,
    provider: Optional[str] = None,
    modality: Optional[str] = None,
) -> Dict[str, dict]:
    """Return cached data filtered by service type, provider, and modality."""
    data = _cache or {}

    if service_type:
        data = {k: v for k, v in data.items() if v.get("service_type") == service_type}

    if provider:
        data = {k: v for k, v in data.items() if v.get("api_identifier") == provider}

    if modality:
        data = {
            k: v
            for k, v in data.items()
            if modality in (v.get("modalities") or [])
        }

    return data


@app.get("/api/pricing")
async def get_pricing(
    service_type: Optional[str] = Query(None, description="Filter by service type (e.g., 'api_endpoint', 'server_rental')"),
    provider: Optional[str] = Query(None, description="Filter by provider (e.g., 'fal', 'openai', 'runway')"),
    modality: Optional[str] = Query(None, description="Filter by modality (e.g., 'text-to-video')"),
) -> Dict[str, dict]:
    """Get pricing data for all models.
    
    Returns a dictionary keyed by model display name with rich metadata.
    Supports filtering by service_type and provider.
    """
    return _get_filtered_data(service_type=service_type, provider=provider, modality=modality)


@app.get("/api/pricing/{model_id}")
async def get_pricing_for_model(model_id: str) -> dict:
    """Get pricing data for a specific model by ID."""
    if not _cache:
        raise HTTPException(status_code=503, detail="Pricing cache not ready")
    model = _cache.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


def _model_record(name: str, payload: dict) -> dict:
    """Return a normalized list-shape record for a model."""
    return {
        "name": name,
        "model_id": payload.get("model_id") or name,
        "provider": payload.get("api_identifier"),
        "service_type": payload.get("service_type"),
        "modalities": payload.get("modalities") or [],
        "display": payload.get("display"),
        "price": payload.get("price"),
        "unit": payload.get("unit"),
        "currency": payload.get("currency"),
        "description": payload.get("description", ""),
        "source": payload.get("source"),
        "last_updated": payload.get("last_updated"),
        "first_seen": payload.get("first_seen"),
        "last_changed": payload.get("last_changed"),
        "status": payload.get("status", "active"),
        "change_count": payload.get("change_count", 0),
        "generation_latency": payload.get("generation_latency"),
        "recommended_use": payload.get("recommended_use"),
        "quality_tier": payload.get("quality_tier"),
        "constraints": payload.get("constraints"),
        "capabilities": payload.get("capabilities"),
        "policy_notes": payload.get("policy_notes"),
        "api_schema": payload.get("api_schema"),
        "thumbnail_url": payload.get("thumbnail_url"),
        "sample_outputs": payload.get("sample_outputs", []),
        "demo_video": payload.get("demo_video"),
        "raw": payload.get("raw"),
    }


@app.get("/api/models")
async def list_models(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    provider: Optional[str] = Query(None, description="Filter by provider code"),
    modality: Optional[str] = Query(None, description="Filter by modality"),
) -> List[dict]:
    """Return models in list shape for clients that prefer array responses."""
    data = _get_filtered_data(service_type=service_type, provider=provider, modality=modality)
    return [_model_record(name, payload) for name, payload in sorted(data.items())]


@app.get("/api/providers")
async def list_providers() -> List[dict]:
    """Return provider summary statistics."""
    data = _cache or {}
    summary: dict[str, dict] = {}

    for payload in data.values():
        code = payload.get("api_identifier", "unknown")
        entry = summary.setdefault(
            code,
            {
                "provider": code,
                "model_count": 0,
                "service_types": set(),
                "modalities": set(),
                "last_updated": None,
            },
        )
        entry["model_count"] += 1
        if payload.get("service_type"):
            entry["service_types"].add(payload["service_type"])
        for modality in payload.get("modalities") or []:
            entry["modalities"].add(modality)

        updated = payload.get("last_updated")
        if updated:
            current = entry["last_updated"]
            entry["last_updated"] = max(updated, current) if current else updated

    provider_list = []
    for entry in summary.values():
        provider_list.append(
            {
                "provider": entry["provider"],
                "model_count": entry["model_count"],
                "service_types": sorted(entry["service_types"]),
                "modalities": sorted(entry["modalities"]),
                "last_updated": entry["last_updated"],
            }
        )

    provider_list.sort(key=lambda item: item["provider"] or "")
    return provider_list


@app.get("/api/modalities")
async def list_modalities() -> List[dict]:
    """Return modalities with associated model counts and providers."""
    data = _cache or {}
    summary: dict[str, dict] = {}

    for payload in data.values():
        for modality in payload.get("modalities") or []:
            entry = summary.setdefault(
                modality,
                {
                    "modality": modality,
                    "model_count": 0,
                    "providers": set(),
                    "service_types": set(),
                },
            )
            entry["model_count"] += 1
            if payload.get("api_identifier"):
                entry["providers"].add(payload["api_identifier"])
            if payload.get("service_type"):
                entry["service_types"].add(payload["service_type"])

    modality_list = []
    for entry in summary.values():
        modality_list.append(
            {
                "modality": entry["modality"],
                "model_count": entry["model_count"],
                "providers": sorted(entry["providers"]),
                "service_types": sorted(entry["service_types"]),
            }
        )

    modality_list.sort(key=lambda item: item["modality"])
    return modality_list


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "updated": _last_updated.isoformat() if _last_updated else None,
        "cache_size": len(_cache) if _cache else 0
    }


@app.get("/api/changes")
async def get_recent_changes() -> dict:
    """Get summary of recent changes (new, changed, deprecated models)."""
    if not _last_change_summary:
        return {
            "message": "No recent changes available",
            "last_update": _last_updated.isoformat() if _last_updated else None
        }
    
    return _last_change_summary


@app.get("/api/models/new")
async def get_new_models(
    days: int = Query(7, description="Number of days to look back for new models"),
    limit: int = Query(50, description="Maximum number of models to return")
) -> List[dict]:
    """Get recently added models."""
    if not _cache:
        raise HTTPException(status_code=503, detail="Pricing cache not ready")
    
    cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
    new_models = []
    
    for model_id, model_data in _cache.items():
        first_seen = model_data.get("first_seen")
        if first_seen:
            try:
                first_seen_dt = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
                if first_seen_dt.timestamp() >= cutoff_date:
                    new_models.append(_model_record(model_id, model_data))
            except (ValueError, TypeError):
                continue
    
    # Sort by first_seen date (newest first)
    new_models.sort(key=lambda x: x.get("first_seen", ""), reverse=True)
    return new_models[:limit]


@app.get("/api/models/changed")
async def get_changed_models(
    days: int = Query(7, description="Number of days to look back for changed models"),
    limit: int = Query(50, description="Maximum number of models to return")
) -> List[dict]:
    """Get recently changed models."""
    if not _cache:
        raise HTTPException(status_code=503, detail="Pricing cache not ready")
    
    cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
    changed_models = []
    
    for model_id, model_data in _cache.items():
        last_changed = model_data.get("last_changed")
        if last_changed:
            try:
                last_changed_dt = datetime.fromisoformat(last_changed.replace('Z', '+00:00'))
                if last_changed_dt.timestamp() >= cutoff_date:
                    record = _model_record(model_id, model_data)
                    record["change_count"] = model_data.get("change_count", 0)
                    changed_models.append(record)
            except (ValueError, TypeError):
                continue
    
    # Sort by last_changed date (most recent first)
    changed_models.sort(key=lambda x: x.get("last_changed", ""), reverse=True)
    return changed_models[:limit]


@app.get("/api/models/deprecated")
async def get_deprecated_models(
    days: int = Query(30, description="Number of days to look back for deprecated models"),
    limit: int = Query(50, description="Maximum number of models to return")
) -> List[dict]:
    """Get recently deprecated models."""
    if not _cache:
        raise HTTPException(status_code=503, detail="Pricing cache not ready")
    
    cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
    deprecated_models = []
    
    for model_id, model_data in _cache.items():
        if model_data.get("status") == "deprecated":
            deprecated_at = model_data.get("deprecated_at")
            if deprecated_at:
                try:
                    deprecated_dt = datetime.fromisoformat(deprecated_at.replace('Z', '+00:00'))
                    if deprecated_dt.timestamp() >= cutoff_date:
                        record = _model_record(model_id, model_data)
                        record["deprecated_at"] = deprecated_at
                        deprecated_models.append(record)
                except (ValueError, TypeError):
                    continue
    
    # Sort by deprecated_at date (most recent first)
    deprecated_models.sort(key=lambda x: x.get("deprecated_at", ""), reverse=True)
    return deprecated_models[:limit]


@app.get("/api/thumbnail/{model_id}")
async def get_model_thumbnail(model_id: str) -> Response:
    """Get thumbnail image for a specific model."""
    if not _cache:
        raise HTTPException(status_code=503, detail="Pricing cache not ready")
    
    model = _cache.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    thumbnail_url = model.get("thumbnail_url")
    if not thumbnail_url:
        raise HTTPException(status_code=404, detail="No thumbnail available for this model")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(thumbnail_url, timeout=10.0)
            response.raise_for_status()
            
            # Determine content type
            content_type = response.headers.get("content-type", "image/jpeg")
            
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch thumbnail: {str(e)}")


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
