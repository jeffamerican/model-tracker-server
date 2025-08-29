# Pricing Service

This service scrapes model pricing information from various providers and serves it over a FastAPI server.

## Running

```bash
pip install -e .
python -m pricing_service.server
```

The server exposes:
- `GET /api/pricing` – list all pricing records
- `GET /api/pricing/{model_id}` – retrieve pricing for a single model

The service periodically refreshes pricing data every 6 hours using the included scraper modules.
