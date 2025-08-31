"""Scraper for OpenAI pricing information."""
from __future__ import annotations

from bs4 import BeautifulSoup
from datetime import datetime
import requests

OPENAI_PRICING_URL = "https://openai.com/pricing"
API_IDENTIFIER = "openai"

# The OpenAI pricing page is served through a CDN that may reject
# requests without typical browser headers.  Supplying a minimal
# ``User-Agent`` and ``Accept`` header prevents 403 responses and lets
# us retrieve the HTML content for scraping.
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_prices() -> dict:
    """Fetch pricing data from OpenAI pricing page."""
    response = requests.get(OPENAI_PRICING_URL, headers=HEADERS, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    data: dict[str, dict] = {}

    # This is a best-effort example; the HTML structure may change and is
    # largely client-rendered.  We scan all ``table`` elements that might
    # contain pricing information.
    for card in soup.select("table"):
        headers = [th.get_text(strip=True) for th in card.select("thead th")]
        service_type = "api_endpoint" if "Model" in headers else "other_service"
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
                    "api_identifier": API_IDENTIFIER,
                    "service_type": service_type,
                    "api_schema": None,
                    "generation_latency": None,
                    "description": None,
                    "last_updated": datetime.utcnow().isoformat(),
                }
    return data
