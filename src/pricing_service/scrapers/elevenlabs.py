"""Scraper for ElevenLabs pricing."""
from __future__ import annotations

from typing import Dict

import re
import requests
from bs4 import BeautifulSoup

ELEVENLABS_PRICING_URL = "https://elevenlabs.io/pricing"
API_IDENTIFIER = "elevenlabs"

PLAN_ORDER = ["Free", "Starter", "Creator", "Pro", "Scale", "Business"]


def fetch_prices() -> Dict[str, Dict]:
    """Fetch ElevenLabs subscription and API usage pricing."""
    response = requests.get(ELEVENLABS_PRICING_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract plan prices
    prices: Dict[str, Dict] = {}
    for card in soup.select("div"):
        h2 = card.find("h2")
        if not h2:
            continue
        name = h2.get_text(strip=True)
        if name not in PLAN_ORDER:
            continue
        price_span = card.find("span", class_="f-heading-03")
        if price_span:
            prices[name] = {"Plan": name, "Price": price_span.get_text(strip=True)}

    # Approximate API usage rates appear as "~$0.xx/minute" once per plan order
    usage_rates = re.findall(r"~\$(\d+\.\d+)/minute", response.text)
    for name, rate in zip(PLAN_ORDER, usage_rates):
        if name not in prices:
            prices[name] = {"Plan": name}
        prices[name]["Usage"] = f"${rate}/minute"

    data: Dict[str, Dict] = {}
    for name, info in prices.items():
        data[f"elevenlabs-{name.lower()}"] = {
            "raw": info,
            "source": ELEVENLABS_PRICING_URL,
            "modalities": ["text-to-speech", "speech-to-speech"],
            "api_identifier": API_IDENTIFIER,
            "service_type": "subscription",
        }
    return data
