# Pricing Service

This service scrapes model pricing information from various providers and serves it over a FastAPI server. Each pricing record includes an `api_identifier` field that names the provider's API so other applications can associate models with their source service.

## Running

```bash
pip install -e .
python -m pricing_service.server
```

The server exposes:
- `GET /api/pricing` – list all pricing records
- `GET /api/pricing/{model_id}` – retrieve pricing for a single model

The service periodically refreshes pricing data every 6 hours using the included scraper modules.

## Web UI

The service includes a web interface for exploring pricing data. Navigate to `/ui/` when the server is running to view a searchable and sortable table:

- Use the search box to filter models by name or pricing details.
- Click any column header to sort by that column.
- Toggle dark mode using the button in the controls.
- Show or hide pricing columns with the column checkboxes.
