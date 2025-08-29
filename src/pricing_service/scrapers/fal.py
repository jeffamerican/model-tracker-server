"""Scraper for fal.ai pricing."""
from __future__ import annotations

from bs4 import BeautifulSoup
import requests

FAL_PRICING_URL = "https://fal.ai/pricing"

# Known model modalities for fal.ai hosted models. These models primarily
# generate video and generally support both text and image prompting.
MODEL_MODALITIES = {
    "Hunyuan Video": ["text-to-video", "image-to-video"],
    "Kling 1.6 Pro Video": ["text-to-video", "image-to-video"],
    "Kling 2 Master Video": ["text-to-video", "image-to-video"],
    "Alibaba Wan Video": ["text-to-video", "image-to-video"],
    "MiniMax Video Live": ["text-to-video", "image-to-video"],
    "LTX-Video 13B 0.9.8 Distilled": ["text-to-video", "image-to-video"],
}


def _parse_table(table: BeautifulSoup) -> list[dict[str, str]]:
    """Convert an HTML table to a list of dictionaries."""
    headers = [
        th.get_text(strip=True).replace("*", "")
        for th in table.select("thead th")
        if th.get_text(strip=True)
    ]
    rows: list[dict[str, str]] = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def fetch_prices() -> dict:
    """Fetch pricing data from fal.ai."""
    response = requests.get(FAL_PRICING_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    data: dict[str, dict] = {}
    tables = soup.select("table")
    if not tables:
        return data

    # GPU pricing (first table)
    for record in _parse_table(tables[0]):
        model_id = record.get("GPU")
        if model_id:
            data[model_id] = {"raw": record, "source": FAL_PRICING_URL}

    # Model pricing (second table)
    if len(tables) > 1:
        for record in _parse_table(tables[1]):
            model_id = record.get("Model")
            if model_id:
                data[model_id] = {"raw": record, "source": FAL_PRICING_URL}

    # Attach known modality information
    for model, modalities in MODEL_MODALITIES.items():
        if model in data:
            data[model]["modalities"] = modalities

    return data
