"""Scraper for Runway pricing."""
from __future__ import annotations

import re
from typing import Dict

import requests
from bs4 import BeautifulSoup

RUNWAY_PRICING_URL = "https://runwayml.com/pricing"
API_IDENTIFIER = "runway"


def fetch_prices() -> Dict[str, Dict]:
    """Fetch Runway subscription and API usage pricing."""
    response = requests.get(RUNWAY_PRICING_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    data: Dict[str, Dict] = {}

    # Free plan price is available directly in the HTML text
    free_price = soup.find(string=re.compile(r"^\$0"))
    if free_price:
        data["runway-free"] = {
            "raw": {"Plan": "Free", "Price": free_price.strip()},
            "source": RUNWAY_PRICING_URL,
            "modalities": ["text-to-video", "image-to-video"],
            "api_identifier": API_IDENTIFIER,
        }

    # Remaining plan prices are comment wrapped like "$<!-- -->12"
    prices = [int(p) for p in re.findall(r"\$<!\-\-\s*-->(\d+)", response.text)]
    # Extract credit and second information. Patterns are repeated, so deduplicate.
    credit_matches = []
    for m in re.finditer(r"Includes\s+(\d+)\s+credits", response.text):
        val = int(m.group(1))
        if val not in credit_matches:
            credit_matches.append(val)
    # Mapping of credits to Gen-4/Gen-4 Turbo seconds
    gen4_seconds = []
    for m in re.finditer(r"(\d+)s of Gen-4,", response.text):
        val = int(m.group(1))
        if val not in gen4_seconds and val != 25:  # ignore free plan example
            gen4_seconds.append(val)
    gen4_turbo_seconds = []
    for m in re.finditer(r"(\d+)s of Gen-4 Turbo", response.text):
        val = int(m.group(1))
        if val not in gen4_turbo_seconds and val != 25:  # ignore free-plan example
            gen4_turbo_seconds.append(val)

    names = ["Standard", "Pro"]
    for name, price, credits, g4_sec, g4_turbo_sec in zip(
        names, prices[:2], credit_matches[1:3], gen4_seconds, gen4_turbo_seconds
    ):
        price_per_sec_g4 = price / g4_sec
        price_per_sec_g4_turbo = price / g4_turbo_sec
        data[f"runway-{name.lower()}"] = {
            "raw": {
                "Plan": name,
                "Price": f"${price}",
                "Gen-4": f"${price_per_sec_g4:.2f}/s",
                "Gen-4 Turbo": f"${price_per_sec_g4_turbo:.2f}/s",
            },
            "source": RUNWAY_PRICING_URL,
            "modalities": ["text-to-video", "image-to-video"],
            "api_identifier": API_IDENTIFIER,
        }

    # Team plan price only (usage cost not derivable without credits)
    if len(prices) >= 3:
        data["runway-team"] = {
            "raw": {"Plan": "Team", "Price": f"${prices[2]}"},
            "source": RUNWAY_PRICING_URL,
            "modalities": ["text-to-video", "image-to-video"],
            "api_identifier": API_IDENTIFIER,
        }

    return data
