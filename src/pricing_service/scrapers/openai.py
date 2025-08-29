"""Scraper for OpenAI pricing information."""
from __future__ import annotations

from bs4 import BeautifulSoup
import requests

OPENAI_PRICING_URL = "https://openai.com/pricing"


def fetch_prices() -> dict:
    """Fetch pricing data from OpenAI pricing page."""
    response = requests.get(OPENAI_PRICING_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    data: dict[str, dict] = {}

    # This is a best-effort example; the HTML structure may change.
    for card in soup.select("section table"):
        headers = [th.get_text(strip=True) for th in card.select("thead th")]
        for row in card.select("tbody tr"):
            cols = [td.get_text(strip=True) for td in row.select("td")]
            if len(cols) != len(headers):
                continue
            record = dict(zip(headers, cols))
            model_id = record.get("Model") or record.get(headers[0])
            if model_id:
                data[model_id] = {
                    "raw": record,
                    "source": OPENAI_PRICING_URL,
                }
    return data
