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
from fastapi.responses import RedirectResponse

from .scraper import write_pricing_file

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


@app.get("/")
async def root() -> RedirectResponse:
    """Redirect to UI."""
    return RedirectResponse(url="/ui/")

_cache: Dict[str, dict] | None = None
_last_updated: Optional[datetime] = None
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


async def _run_write_task() -> dict:
    """Run the blocking scraper pipeline in a background thread."""
    return await asyncio.to_thread(write_pricing_file, DATA_PATH)


async def _refresh_cache() -> None:
    """Populate the in-memory cache with fresh data."""
    global _cache, _last_updated
    _cache = _normalize_cache(await _run_write_task())
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
        _cache = _normalize_cache(json.loads(DATA_PATH.read_text()))
        _last_updated = datetime.utcnow()
    else:
        # Start with empty cache and refresh in background
        _cache = {}
        _last_updated = None
    # Start background tasks
    asyncio.create_task(refresh_pricing())


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
        "generation_latency": payload.get("generation_latency"),
        "recommended_use": payload.get("recommended_use"),
        "quality_tier": payload.get("quality_tier"),
        "constraints": payload.get("constraints"),
        "capabilities": payload.get("capabilities"),
        "policy_notes": payload.get("policy_notes"),
        "api_schema": payload.get("api_schema"),
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
