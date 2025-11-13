"""Aggregate pricing data from provider scrapers."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Iterable, Dict, Set, Tuple

SCRAPER_MODULES: Iterable[str] = [
    "pricing_service.scrapers.openai",
    "pricing_service.scrapers.fal",
    "pricing_service.scrapers.runway",
    "pricing_service.scrapers.hedra",
    "pricing_service.scrapers.elevenlabs",
    "pricing_service.scrapers.gemini",
]


def _calculate_model_hash(model_data: dict) -> str:
    """Calculate a hash for model data to detect changes."""
    # Create a normalized version for hashing (exclude metadata fields)
    normalized = {
        "model_id": model_data.get("model_id"),
        "raw": model_data.get("raw"),
        "api_identifier": model_data.get("api_identifier"),
        "service_type": model_data.get("service_type"),
        "price": model_data.get("price"),
        "unit": model_data.get("unit"),
        "currency": model_data.get("currency"),
        "description": model_data.get("description"),
        "display": model_data.get("display"),
        "modalities": model_data.get("modalities"),
        "constraints": model_data.get("constraints"),
        "capabilities": model_data.get("capabilities"),
        "policy_notes": model_data.get("policy_notes"),
        "api_schema": model_data.get("api_schema"),
    }
    # Convert to JSON string and hash
    json_str = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.md5(json_str.encode()).hexdigest()


def _add_model_metadata(model_data: dict, is_new: bool = False, previous_hash: str = None) -> dict:
    """Add tracking metadata to a model record."""
    now = datetime.utcnow().isoformat()
    
    # Preserve existing metadata if updating
    if not is_new and "first_seen" in model_data:
        # Keep existing first_seen date
        pass
    else:
        model_data["first_seen"] = now
    
    model_data["last_updated"] = now
    model_data["data_hash"] = _calculate_model_hash(model_data)
    model_data["status"] = "active"
    
    # Track if this is a change from previous version
    if previous_hash and previous_hash != model_data["data_hash"]:
        model_data["last_changed"] = now
        model_data["change_count"] = model_data.get("change_count", 0) + 1
    
    return model_data


def run_scrapers() -> dict:
    """Run all scraper modules and combine results."""
    combined: dict[str, dict] = {}
    for module_name in SCRAPER_MODULES:
        module = import_module(module_name)
        if hasattr(module, "fetch_prices"):
            try:
                data = module.fetch_prices()
                combined.update(data)
            except Exception as exc:  # pragma: no cover - network errors
                print(f"Failed to run scraper {module_name}: {exc}")
    return combined


def incremental_update_pricing_file(path: Path) -> Tuple[dict, dict]:
    """Update pricing file incrementally, preserving existing data and tracking changes.
    
    Returns:
        Tuple of (updated_data, change_summary) where change_summary contains:
        - new_models: List of newly discovered models
        - changed_models: List of models with updated data
        - deprecated_models: List of models no longer found
    """
    # Load existing data
    existing_data = {}
    if path.exists():
        try:
            existing_data = json.loads(path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = {}
    
    # Get fresh data from scrapers
    fresh_data = run_scrapers()
    
    # Track changes
    change_summary = {
        "new_models": [],
        "changed_models": [],
        "deprecated_models": [],
        "update_timestamp": datetime.utcnow().isoformat()
    }
    
    # Process each fresh model
    updated_data = existing_data.copy()
    
    for model_id, model_data in fresh_data.items():
        is_new = model_id not in existing_data
        previous_hash = existing_data.get(model_id, {}).get("data_hash") if not is_new else None
        
        # Add metadata
        model_data = _add_model_metadata(model_data, is_new=is_new, previous_hash=previous_hash)
        
        if is_new:
            change_summary["new_models"].append(model_id)
        elif previous_hash and previous_hash != model_data["data_hash"]:
            change_summary["changed_models"].append(model_id)
        
        updated_data[model_id] = model_data
    
    # Mark models as deprecated if they're no longer found
    existing_model_ids = set(existing_data.keys())
    fresh_model_ids = set(fresh_data.keys())
    deprecated_ids = existing_model_ids - fresh_model_ids
    
    for model_id in deprecated_ids:
        if updated_data[model_id].get("status") != "deprecated":
            updated_data[model_id]["status"] = "deprecated"
            updated_data[model_id]["deprecated_at"] = datetime.utcnow().isoformat()
            change_summary["deprecated_models"].append(model_id)
    
    # Write updated data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(updated_data, indent=2))
    
    return updated_data, change_summary


def write_pricing_file(path: Path) -> dict:
    """Run scrapers and write JSON to `path` (legacy full rebuild method)."""
    data = run_scrapers()
    path.write_text(json.dumps(data, indent=2))
    return data


if __name__ == "__main__":  # pragma: no cover
    write_pricing_file(Path(__file__).resolve().parents[2] / "data" / "model_pricing.json")
