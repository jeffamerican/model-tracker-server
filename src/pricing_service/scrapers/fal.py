"""Scraper for fal.ai pricing."""
from __future__ import annotations

from bs4 import BeautifulSoup
import requests

FAL_PRICING_URL = "https://fal.ai/pricing"


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


    for table in tables:
        headers = [
            th.get_text(strip=True).replace("*", "")
            for th in table.select("thead th")
            if th.get_text(strip=True)
        ]
        records = _parse_table(table)
        if "GPU" in headers:
            key = "GPU"
        elif "Model" in headers:
            key = "Model"
        else:
            continue
        for record in records:
            model_id = record.get(key)
     main
            if model_id:
                data[model_id] = {"raw": record, "source": FAL_PRICING_URL}

    return data
