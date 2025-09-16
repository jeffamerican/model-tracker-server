"""Scraper for OpenAI pricing information."""
from __future__ import annotations

from bs4 import BeautifulSoup
from datetime import datetime
import requests
import re

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


def _generate_openai_schema(model_id: str) -> dict:
    """Generate API schema for OpenAI models."""
    base_schema = {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "description": "List of messages in the conversation",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "enum": ["system", "user", "assistant"],
                            "description": "Role of the message sender"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content of the message"
                        }
                    },
                    "required": ["role", "content"]
                }
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum number of tokens to generate",
                "minimum": 1,
                "maximum": 128000 if "gpt-4" in model_id.lower() else 32000
            },
            "temperature": {
                "type": "number",
                "description": "Sampling temperature (0.0 to 2.0)",
                "minimum": 0.0,
                "maximum": 2.0,
                "default": 1.0
            }
        },
        "required": ["messages"]
    }
    
    # Add model-specific fields
    if "dall-e" in model_id.lower():
        base_schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the image to generate"
                },
                "n": {
                    "type": "integer",
                    "description": "Number of images to generate",
                    "minimum": 1,
                    "maximum": 4,
                    "default": 1
                },
                "size": {
                    "type": "string",
                    "enum": ["1024x1024", "1024x1792", "1792x1024"],
                    "description": "Size of the generated image",
                    "default": "1024x1024"
                }
            },
            "required": ["prompt"]
        }
    
    return base_schema


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
                # Extract pricing information for display
                input_price = record.get("Input", "")
                output_price = record.get("Output", "")
                display_price = None
                
                if input_price and output_price:
                    display_price = f"Input: {input_price}, Output: {output_price}"
                elif input_price:
                    display_price = f"Input: {input_price}"
                elif output_price:
                    display_price = f"Output: {output_price}"
                
                # Generate description
                description = f"OpenAI {model_id} model"
                
                # Generate canonical model_id
                model_id_canonical = f"openai/{model_id.lower().replace(' ', '-').replace(':', '')}"
                
                # Extract pricing components
                input_price_value = None
                output_price_value = None
                if input_price:
                    input_match = re.search(r'\$(\d+(?:\.\d+)?)', input_price)
                    input_price_value = float(input_match.group(1)) if input_match else None
                if output_price:
                    output_match = re.search(r'\$(\d+(?:\.\d+)?)', output_price)
                    output_price_value = float(output_match.group(1)) if output_match else None
                
                # Generate API schema for OpenAI models
                api_schema = _generate_openai_schema(model_id)
                
                # Determine modalities based on model type
                modalities = ["text-generation"]
                if "dall-e" in model_id.lower() or "dalle" in model_id.lower():
                    modalities = ["text-to-image"]
                elif "whisper" in model_id.lower():
                    modalities = ["speech-to-text"]
                elif "tts" in model_id.lower():
                    modalities = ["text-to-speech"]
                
                data[model_id] = {
                    "model_id": model_id_canonical,
                    "raw": record,
                    "source": OPENAI_PRICING_URL,
                    "api_identifier": API_IDENTIFIER,
                    "service_type": service_type,
                    "api_schema": api_schema,
                    "generation_latency": None,
                    "description": description,
                    "display": display_price,
                    "price": input_price_value,  # Primary price (input)
                    "unit": "per_1k_tokens",
                    "currency": "USD",
                    "last_updated": datetime.utcnow().isoformat(),
                    "recommended_use": f"Language model for text generation and completion",
                    "quality_tier": "premium" if "gpt-4" in model_id.lower() else "standard",
                    "modalities": modalities,
                    "constraints": {
                        "max_tokens": 128000 if "gpt-4" in model_id.lower() else 32000,
                        "context_window": "large" if "gpt-4" in model_id.lower() else "standard"
                    },
                    "capabilities": ["text_generation", "completion", "chat"],
                    "policy_notes": "Token-based pricing with usage limits"
                }
    return data
