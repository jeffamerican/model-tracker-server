"""Scraper for fal.ai pricing."""
from __future__ import annotations

from bs4 import BeautifulSoup
from fal_client import SyncClient
from datetime import datetime
import string
import re

FAL_PRICING_URL = "https://fal.ai/pricing"
EXPLORER_SEARCH_URL = "https://fal.ai/explore/search"
MODEL_BASE_URL = "https://fal.ai/models"
API_IDENTIFIER = "fal"

# Search queries used to progressively discover new models. This list
# intentionally covers common starting characters and will grow the
# scraped dataset over time as more runs are performed.
# Begin with popular queries to ensure high-value endpoints are captured
# even when the discovery limit is reached early.
SEARCH_QUERIES = ["", "k", "v"] + [
    c for c in string.ascii_lowercase + string.digits if c not in {"k", "v"}
]

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


CLIENT = SyncClient(key="0")


def _get(url: str, **kwargs):
    """Wrapper around the fal client to issue HTTP GET requests."""
    return CLIENT._client.get(url, **kwargs)


def _discover_model_slugs(limit: int = 10) -> list[str]:
    """Return a list of model slugs discovered via the explore search page."""
    slugs: list[str] = []
    seen: set[str] = set()
    for query in SEARCH_QUERIES:
        if len(slugs) >= limit:
            break
        try:
            resp = _get(EXPLORER_SEARCH_URL, params={"q": query}, timeout=10)
            resp.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for link in soup.select("a.page-model-card"):
            href = link.get("href", "")
            if "/models/" not in href:
                continue
            slug = href.split("/models/")[-1].strip("/")
            if slug and slug not in seen:
                seen.add(slug)
                slugs.append(slug)
                if len(slugs) >= limit:
                    break
    return slugs


def _extract_price(slug: str) -> str | None:
    """Extract a price snippet from a model page if available."""
    url = f"{MODEL_BASE_URL}/{slug}"
    try:
        resp = _get(url, timeout=10)
        resp.raise_for_status()
    except Exception:
        return None
    html = resp.text.replace("<!--$-->", "").replace("<!--/$-->", "")
    soup = BeautifulSoup(html, "html.parser")
    texts = [
        t.strip(": \n")
        for t in soup.find_all(string=lambda s: s and "$" in s)
        if t.strip()
    ]
    texts = [t for t in texts if t != "$"]
    if texts:
        return " ".join(texts[:2])
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and "$" in meta.get("content", ""):
        return meta["content"]
    return None


def _extract_api_details(slug: str) -> tuple[str | None, str | None, str | None]:
    """Return usage schema, generation latency, and description from a model page if present."""
    url = f"{MODEL_BASE_URL}/{slug}"
    try:
        resp = _get(url, timeout=10)
        resp.raise_for_status()
    except Exception:
        return None, None, None
    html = resp.text.replace("<!--$-->", "").replace("<!--/$-->", "")
    soup = BeautifulSoup(html, "html.parser")
    schema = None
    code = soup.select_one("pre code")
    if code:
        text = code.get_text(strip=True)
        if text:
            schema = text
    latency = None
    text_blob = soup.get_text(" ", strip=True).lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)", text_blob)
    if match:
        latency = f"{match.group(1)}s"
    description = None
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        description = meta.get("content")
    return schema, latency, description


def _fetch_explore_data(existing: set[str]) -> dict[str, dict]:
    """Fetch model data from the explore search endpoints."""
    results: dict[str, dict] = {}
    for slug in _discover_model_slugs():
        if slug in existing or slug in results:
            continue
        price = _extract_price(slug)
        record: dict[str, object] = {
            "raw": {"endpoint": slug},
            "source": f"{MODEL_BASE_URL}/{slug}",
            "api_identifier": API_IDENTIFIER,
            "service_type": "api_endpoint",
            "api_schema": None,
            "generation_latency": None,
            "description": None,
            "last_updated": datetime.utcnow().isoformat(),
        }
        if price:
            record["raw"]["price"] = price
        modality = slug.split("/")[-1]
        if "-" in modality:
            record["modalities"] = [modality]
        schema, latency, description = _extract_api_details(slug)
        if schema:
            record["api_schema"] = schema
        if latency:
            record["generation_latency"] = latency
        if description:
            record["description"] = description
        results[slug] = record
    return results


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
    response = _get(FAL_PRICING_URL, timeout=10)
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
            data[model_id] = {
                "raw": record,
                "source": FAL_PRICING_URL,
                "api_identifier": API_IDENTIFIER,
                "service_type": "server_rental",
                "api_schema": None,
                "generation_latency": None,
                "description": None,
                "last_updated": datetime.utcnow().isoformat(),
            }

    # Model pricing (second table)
    if len(tables) > 1:
        for record in _parse_table(tables[1]):
            model_id = record.get("Model")
            if model_id:
                data[model_id] = {
                    "raw": record,
                    "source": FAL_PRICING_URL,
                    "api_identifier": API_IDENTIFIER,
                    "service_type": "api_endpoint",
                    "api_schema": None,
                    "generation_latency": None,
                    "description": None,
                    "last_updated": datetime.utcnow().isoformat(),
                }

    # Attach known modality information
    for model, modalities in MODEL_MODALITIES.items():
        if model in data:
            data[model]["modalities"] = modalities
    # Discover additional models from the explore search page
    data.update(_fetch_explore_data(set(data.keys())))

    return data
