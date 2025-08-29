"""Scraper for Hedra pricing.

The Hedra website currently does not expose pricing
information without JavaScript.  This scraper attempts to fetch the
pricing page and returns a placeholder when unavailable.
"""
from __future__ import annotations

from typing import Dict

import requests

HEDRA_PRICING_URL = "https://hedra.com/pricing"
API_IDENTIFIER = "hedra"


def fetch_prices() -> Dict[str, Dict]:
    """Best-effort fetch for Hedra pricing."""
    try:
        response = requests.get(HEDRA_PRICING_URL, timeout=10)
        if response.status_code != 200:
            raise requests.HTTPError(f"status {response.status_code}")
    except Exception as exc:  # pragma: no cover - network errors
        return {
            "hedra": {
                "raw": {"error": str(exc)},
                "source": HEDRA_PRICING_URL,
                "modalities": ["speech-to-video", "text-to-video"],
                "api_identifier": API_IDENTIFIER,
            }
        }

    # If the request succeeds but contains no pricing info, return notice
    return {
        "hedra": {
            "raw": {"message": "Pricing page accessible but data not parsed"},
            "source": HEDRA_PRICING_URL,
            "modalities": ["speech-to-video", "text-to-video"],
            "api_identifier": API_IDENTIFIER,
        }
    }
