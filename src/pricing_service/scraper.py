"""Aggregate pricing data from provider scrapers."""
from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Iterable

SCRAPER_MODULES: Iterable[str] = [
    "pricing_service.scrapers.openai",
    "pricing_service.scrapers.fal",
    "pricing_service.scrapers.runway",
    "pricing_service.scrapers.hedra",
    "pricing_service.scrapers.elevenlabs",
    "pricing_service.scrapers.gemini",
]


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


def write_pricing_file(path: Path) -> dict:
    """Run scrapers and write JSON to `path`."""
    data = run_scrapers()
    path.write_text(json.dumps(data, indent=2))
    return data


if __name__ == "__main__":  # pragma: no cover
    write_pricing_file(Path(__file__).resolve().parents[2] / "data" / "model_pricing.json")
