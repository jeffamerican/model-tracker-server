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

# Comprehensive search queries to discover all available models.
# This list includes popular model types, techniques, and provider names
# to ensure maximum model discovery across all categories.
SEARCH_QUERIES = [
    # Core searches - empty and popular letters first
    "", "k", "v", "a", "b", "c", "d", "f", "i", "l", "m", "s", "t", "u",
    
    # Model types and techniques
    "video", "image", "audio", "text", "speech", "music", "voice", "3d",
    "flux", "lora", "controlnet", "inpainting", "upscale", "enhance", "edit",
    "diffusion", "transformer", "generation", "style", "portrait", "anime",
    "realistic", "cartoon", "sketch", "painting", "photo", "art",
    
    # Popular model families
    "stable", "runway", "midjourney", "dalle", "gpt", "claude", "llama",
    "whisper", "bark", "elevenlabs", "suno", "udio", "minimax", "kling",
    "hunyuan", "ltx", "alibaba", "wan", "dream", "machine", "schnell",
    "ultra", "pro", "turbo", "xl", "hd", "4k", "fast", "slow", "quality",
    
    # Bytedance and related terms
    "bytedance", "tiktok", "douyin", "seedream", "seed", "seeddream",
    "cogvideox", "cog", "cogvideo", "beijing", "china", "douyin-ai",
    "seedance", "seededit", "dreamina", "omnihuman", "cogview",
    
    # Qwen and Alibaba Cloud models
    "qwen", "qwen2", "qwen2.5", "qwenvl", "alibaba", "aliyun", "tongyi",
    "qwen-vl", "qwen-audio", "qwen-coder", "qwen-math", "qwen-chat",
    
    # Google and DeepMind models  
    "google", "deepmind", "gemini", "imagen", "bard", "veo", "lumiere",
    "imagen2", "imagen3", "veo2", "gemma", "palm", "lamda", "musiclm",
    "phenaki", "parti", "flamingo", "chinchilla", "gopher", "sparrow",
    
    # Video Generation Companies and Models
    "luma", "lumalabs", "dream-machine", "photon", "ray", "luma-ai",
    "pixverse", "pixart", "pix2pix", "pixe", "pix",
    "kling", "kuaishou", "klingai", "kling-ai", "kwai",
    "hailuo", "minimax", "hailuo-ai", "hailuoai", "hai",
    
    # Technical terms
    "api", "endpoint", "model", "ai", "ml", "neural", "deep", "learning",
    "inference", "training", "fine-tune", "custom", "base", "foundation",
    
    # Remaining alphabet and digits for completeness
] + [c for c in string.ascii_lowercase + string.digits if c not in {"k", "v", "a", "b", "c", "d", "f", "i", "l", "m", "s", "t", "u"}]

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

def _infer_modalities_from_slug(slug: str) -> list[str]:
    """
    Infer modalities from model slug based on common patterns.
    
    Args:
        slug: Model slug (e.g., "fal-ai/flux-pro/kontext")
        
    Returns:
        List of inferred modalities
    """
    slug_lower = slug.lower()
    modalities = []
    
    # Video generation patterns
    if any(pattern in slug_lower for pattern in ["video", "kling", "hunyuan", "minimax", "ltx", "veo", "wan"]):
        if "image-to-video" in slug_lower:
            modalities.append("image-to-video")
        elif "text-to-video" in slug_lower:
            modalities.append("text-to-video")
        elif "audio-to-video" in slug_lower:
            modalities.append("audio-to-video")
        elif any(video_term in slug_lower for video_term in ["video", "kling", "hunyuan", "minimax", "ltx", "veo"]):
            # Default to both text and image for video models
            modalities.extend(["text-to-video", "image-to-video"])
    
    # Image generation patterns
    elif any(pattern in slug_lower for pattern in ["image", "flux", "stable-diffusion", "dalle", "midjourney", "dall-e"]):
        if "image-to-image" in slug_lower:
            modalities.append("image-to-image")
        elif "text-to-image" in slug_lower:
            modalities.append("text-to-image")
        elif any(img_term in slug_lower for img_term in ["image", "flux", "stable-diffusion", "dalle", "midjourney"]):
            modalities.append("text-to-image")
    
    # Audio patterns
    elif any(pattern in slug_lower for pattern in ["audio", "tts", "speech", "whisper", "voice"]):
        if "text-to-audio" in slug_lower or "tts" in slug_lower:
            modalities.append("text-to-speech")
        elif "speech-to-text" in slug_lower or "whisper" in slug_lower:
            modalities.append("speech-to-text")
        elif "audio-to-video" in slug_lower:
            modalities.append("audio-to-video")
        elif "video-to-audio" in slug_lower:
            modalities.append("video-to-audio")
        else:
            modalities.append("audio-processing")
    
    # Text processing patterns
    elif any(pattern in slug_lower for pattern in ["text", "llm", "gpt", "claude", "llama", "gemini"]):
        if "text-to-text" in slug_lower:
            modalities.append("text-generation")
        else:
            modalities.append("text-generation")
    
    # Specialized processing patterns
    elif "upscale" in slug_lower:
        modalities.append("image-upscaling")
    elif "inpaint" in slug_lower:
        modalities.append("image-inpainting")
    elif "controlnet" in slug_lower:
        modalities.append("image-control")
    elif "lora" in slug_lower:
        modalities.append("model-training")
    elif "trainer" in slug_lower:
        modalities.append("model-training")
    elif "detection" in slug_lower:
        modalities.append("object-detection")
    elif "understanding" in slug_lower:
        modalities.append("content-understanding")
    
    # Default fallback based on common terms
    else:
        # Try to infer from the last part of the slug
        last_part = slug.split("/")[-1].lower()
        if "-" in last_part:
            # If it has hyphens, try to parse as modality
            potential_modality = last_part.replace("-", "-")
            if any(term in potential_modality for term in ["to-", "generation", "processing"]):
                modalities.append(potential_modality)
        
        # If still no modalities found, add a generic one
        if not modalities:
            modalities.append("ai-processing")
    
    return modalities


CLIENT = SyncClient(key="0")


def _get(url: str, **kwargs):
    """Wrapper around the fal client to issue HTTP GET requests."""
    return CLIENT._client.get(url, **kwargs)


def _discover_model_slugs(limit: int = None) -> list[str]:
    """Return a list of model slugs discovered via the explore search page.
    
    Args:
        limit: Maximum number of models to discover. If None, discovers all available models.
        
    Returns:
        List of unique model slugs found across all search queries.
    """
    import time
    
    slugs: list[str] = []
    seen: set[str] = set()
    
    print(f"Starting comprehensive model discovery across {len(SEARCH_QUERIES)} search queries...")
    
    for i, query in enumerate(SEARCH_QUERIES):
        if limit and len(slugs) >= limit:
            break
            
        try:
            # Add rate limiting - respectful 1 second delay between requests
            if i > 0:
                time.sleep(1)
                
            resp = _get(EXPLORER_SEARCH_URL, params={"q": query}, timeout=15)
            resp.raise_for_status()
            
        except Exception as e:
            print(f"Failed to search query '{query}': {e}")
            continue
            
        soup = BeautifulSoup(resp.text, "html.parser")
        query_models = 0
        
        for link in soup.select("a.page-model-card"):
            href = link.get("href", "")
            if "/models/" not in href:
                continue
            slug = href.split("/models/")[-1].strip("/")
            if slug and slug not in seen:
                seen.add(slug)
                slugs.append(slug)
                query_models += 1
                if limit and len(slugs) >= limit:
                    break
                    
        if query_models > 0:
            print(f"Query '{query}': found {query_models} new models (total: {len(slugs)})")
            
    print(f"Model discovery complete: {len(slugs)} unique models found")
    return slugs


def _extract_price(slug: str) -> tuple[str | None, str | None]:
    """Extract price information from a model page if available.
    
    Returns:
        Tuple of (display_price, raw_price) where display_price is formatted for UI
        and raw_price contains the numeric value and unit.
    """
    url = f"{MODEL_BASE_URL}/{slug}"
    try:
        resp = _get(url, timeout=10)
        resp.raise_for_status()
    except Exception:
        return None, None
    
    html = resp.text.replace("<!--$-->", "").replace("<!--/$-->", "")
    soup = BeautifulSoup(html, "html.parser")
    
    # Look for price information in various formats
    texts = [
        t.strip(": \n")
        for t in soup.find_all(string=lambda s: s and "$" in s)
        if t.strip()
    ]
    texts = [t for t in texts if t != "$"]
    
    display_price = None
    raw_price = None
    
    if texts:
        price_text = " ".join(texts[:2])
        display_price = price_text
        
        # Try to extract numeric price and unit
        price_match = re.search(r'\$(\d+(?:\.\d+)?)\s*/\s*(\w+)', price_text)
        if price_match:
            amount = float(price_match.group(1))
            unit = price_match.group(2)
            raw_price = {"amount": amount, "unit": f"per_{unit}", "currency": "USD"}
    
    # Fallback to meta description
    if not display_price:
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and "$" in meta.get("content", ""):
            display_price = meta["content"]
    
    return display_price, raw_price


def _generate_gpu_schema(model_id: str, record: dict) -> dict:
    """Generate API schema for GPU rental models."""
    return {
        "type": "object",
        "properties": {
            "duration_hours": {
                "type": "number",
                "description": "Rental duration in hours",
                "minimum": 0.1,
                "maximum": 24,
                "default": 1
            },
            "framework": {
                "type": "string",
                "enum": ["pytorch", "tensorflow", "jax", "huggingface"],
                "description": "ML framework to use",
                "default": "pytorch"
            },
            "workload_type": {
                "type": "string",
                "enum": ["training", "inference", "fine-tuning", "custom"],
                "description": "Type of workload to run",
                "default": "inference"
            }
        },
        "required": ["duration_hours"]
    }


def _generate_api_schema(model_id: str, unit: str) -> dict:
    """Generate API schema based on model type and unit."""
    base_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text prompt for generation"
            }
        },
        "required": ["prompt"]
    }
    
    # Add unit-specific fields
    if "video" in unit.lower():
        base_schema["properties"].update({
            "duration": {
                "type": "number",
                "description": "Video duration in seconds",
                "minimum": 1,
                "maximum": 30
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16", "1:1"],
                "description": "Video aspect ratio"
            }
        })
    elif "image" in unit.lower():
        base_schema["properties"].update({
            "width": {
                "type": "integer",
                "description": "Image width in pixels",
                "minimum": 256,
                "maximum": 2048
            },
            "height": {
                "type": "integer", 
                "description": "Image height in pixels",
                "minimum": 256,
                "maximum": 2048
            }
        })
    
    return base_schema


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
    import time
    
    results: dict[str, dict] = {}
    discovered_slugs = _discover_model_slugs()
    
    print(f"Processing {len(discovered_slugs)} discovered models...")
    
    for i, slug in enumerate(discovered_slugs):
        if slug in existing or slug in results:
            continue
            
        try:
            # Rate limiting between individual model requests
            if i > 0 and i % 10 == 0:  # Pause every 10 models
                print(f"Processed {i} models, taking a brief pause...")
                time.sleep(2)
                
            display_price, raw_price = _extract_price(slug)
            
            # Generate canonical model_id
            model_id_canonical = f"fal-ai/{slug}"
            
            # Generate API schema for explore models
            api_schema = _generate_api_schema(slug, "generation")
            
            record: dict[str, object] = {
                "model_id": model_id_canonical,
                "raw": {"endpoint": slug},
                "source": f"{MODEL_BASE_URL}/{slug}",
                "api_identifier": API_IDENTIFIER,
                "service_type": "api_endpoint",
                "api_schema": api_schema,
                "generation_latency": None,
                "description": f"AI model endpoint: {slug}",
                "last_updated": datetime.utcnow().isoformat(),
                "recommended_use": f"API endpoint for {slug} model",
                "quality_tier": "standard",
                "constraints": {
                    "max_batch": 5,
                    "rate_limit": "per_minute"
                },
                "capabilities": ["api_access", "generation"],
                "policy_notes": "API access with rate limiting"
            }
            
            # Add pricing information
            if display_price:
                record["display"] = display_price
            if raw_price:
                record["raw"].update(raw_price)
                record["price"] = raw_price.get("amount")
                record["unit"] = raw_price.get("unit")
                record["currency"] = raw_price.get("currency", "USD")
            # Use the new modality inference system
            inferred_modalities = _infer_modalities_from_slug(slug)
            if inferred_modalities:
                record["modalities"] = inferred_modalities
            schema, latency, description = _extract_api_details(slug)
            if schema:
                record["api_schema"] = schema
            if latency:
                record["generation_latency"] = latency
            if description:
                record["description"] = description
            results[slug] = record
            
            if (i + 1) % 50 == 0:  # Progress indicator every 50 models
                print(f"Progress: {i + 1}/{len(discovered_slugs)} models processed")
                
        except Exception as e:
            print(f"Failed to process model {slug}: {e}")
            continue
            
    print(f"Explore data processing complete: {len(results)} new models added")
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
            # Extract pricing information
            price_per_hour = record.get("Price per hour", "")
            price_per_second = record.get("Price per second", "")
            
            # Generate canonical model_id
            model_id_canonical = f"fal-ai/{model_id.lower().replace(' ', '-')}"
            
            # Generate GPU rental schema
            gpu_schema = _generate_gpu_schema(model_id, record)
            
            data[model_id] = {
                "model_id": model_id_canonical,
                "raw": record,
                "source": FAL_PRICING_URL,
                "api_identifier": API_IDENTIFIER,
                "service_type": "server_rental",
                "api_schema": gpu_schema,
                "generation_latency": None,
                "description": f"GPU server rental - {record.get('VRAM', 'Unknown VRAM')}",
                "display": price_per_hour if price_per_hour else price_per_second,
                "last_updated": datetime.utcnow().isoformat(),
                "recommended_use": f"High-performance GPU compute for {record.get('VRAM', 'AI workloads')}",
                "quality_tier": "premium",
                "constraints": {
                    "max_duration_hours": 24,
                    "supported_frameworks": ["pytorch", "tensorflow", "jax"]
                },
                "capabilities": ["gpu_compute", "ai_training", "inference"],
                "policy_notes": "Hourly billing with automatic scaling"
            }

    # Model pricing (second table)
    if len(tables) > 1:
        for record in _parse_table(tables[1]):
            model_id = record.get("Model")
            if model_id:
                # Extract pricing information
                price = record.get("Price", "")
                unit = record.get("Unit", "")
                display_price = f"${price} / {unit}" if price and unit else price
                
                # Generate description based on model name
                description = f"AI model for {model_id.lower().replace(' ', ' ')}"
                
                # Generate canonical model_id
                model_id_canonical = f"fal-ai/{model_id.lower().replace(' ', '-').replace(':', '')}"
                
                # Extract pricing components
                price_match = re.search(r'\$(\d+(?:\.\d+)?)', price)
                price_value = float(price_match.group(1)) if price_match else None
                
                # Generate API schema based on model type
                api_schema = _generate_api_schema(model_id, unit)
                
                data[model_id] = {
                    "model_id": model_id_canonical,
                    "raw": record,
                    "source": FAL_PRICING_URL,
                    "api_identifier": API_IDENTIFIER,
                    "service_type": "api_endpoint",
                    "api_schema": api_schema,
                    "generation_latency": None,
                    "description": description,
                    "display": display_price,
                    "price": price_value,
                    "unit": unit,
                    "currency": "USD",
                    "last_updated": datetime.utcnow().isoformat(),
                    "recommended_use": f"High-quality {unit} generation with {model_id}",
                    "quality_tier": "standard" if "pro" not in model_id.lower() else "premium",
                    "constraints": {
                        "max_batch": 10,
                        "supported_formats": ["mp4", "webm"] if "video" in unit else ["png", "jpg"]
                    },
                    "capabilities": ["generation", "api_access"],
                    "policy_notes": "Pay-per-use pricing with API access"
                }

    # Attach known modality information
    for model, modalities in MODEL_MODALITIES.items():
        if model in data:
            data[model]["modalities"] = modalities
    
    # Discover additional models from the explore search page
    data.update(_fetch_explore_data(set(data.keys())))
    
    # Ensure all models have modalities - infer for any that don't
    for model_id, model_data in data.items():
        if "modalities" not in model_data or not model_data["modalities"]:
            # Extract slug from model_id for inference
            if "/" in model_id:
                slug = model_id.split("/", 1)[1]  # Remove provider prefix
                inferred_modalities = _infer_modalities_from_slug(slug)
                if inferred_modalities:
                    model_data["modalities"] = inferred_modalities

    return data
