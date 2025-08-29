"""Scraper for Google Gemini pricing."""
from __future__ import annotations

from typing import Dict

import requests
from bs4 import BeautifulSoup

GEMINI_PRICING_URL = "https://ai.google.dev/pricing"
API_IDENTIFIER = "gemini"

# Gemini models accept multimodal inputs (text, images, audio, video) and
# produce text outputs.
GEMINI_MODALITIES = [
    "text-to-text",
    "image-to-text",
    "audio-to-text",
    "video-to-text",
]


def fetch_prices() -> Dict[str, Dict]:
    """Fetch Gemini model pricing tables."""
    response = requests.get(GEMINI_PRICING_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    data: Dict[str, Dict] = {}
    for heading in soup.select("h2, h3"):
        model = heading.get_text(strip=True)
        table = heading.find_next("table")
        if not table:
            continue
        headers = [th.get_text(strip=True) for th in table.select("thead th")]
        rows = {}
        for tr in table.select("tbody tr"):
            cols = [td.get_text(strip=True) for td in tr.select("td")]
            if len(cols) != len(headers):
                continue
            row_name = cols[0]
            rows[row_name] = dict(zip(headers[1:], cols[1:]))
        if rows:
            data[model] = {
                "raw": rows,
                "source": GEMINI_PRICING_URL,
                "modalities": GEMINI_MODALITIES,
                "api_identifier": API_IDENTIFIER,
            }
    return data
