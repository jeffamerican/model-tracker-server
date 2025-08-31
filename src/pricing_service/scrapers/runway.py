"""Scraper for Runway account information using the official SDK."""
from __future__ import annotations

import os
from typing import Dict

from datetime import datetime
from runwayml import RunwayML, RunwayMLError

API_IDENTIFIER = "runway"


def fetch_prices() -> Dict[str, Dict]:
    """Fetch Runway organization details via the SDK.

    The endpoint requires an API key. If authentication fails, an empty
    dictionary is returned. No pricing information is exposed via the API,
    so only the raw organization response is stored when available.
    """

    api_key = os.getenv("RUNWAY_API_KEY", "key_placeholder")
    client = RunwayML(api_key=api_key)
    data: Dict[str, Dict] = {}

    try:
        org = client.organization.retrieve()
        usage = client.organization.retrieve_usage()
    except RunwayMLError:
        return data

    data["runway-organization"] = {
        "raw": {
            "organization": org.model_dump(),
            "usage": usage.model_dump(),
        },
        "source": "https://api.runwayml.com/v1/organization",
        "api_identifier": API_IDENTIFIER,
        "service_type": "subscription",
        "api_schema": None,
        "generation_latency": None,
        "description": None,
        "last_updated": datetime.utcnow().isoformat(),
    }

    return data

