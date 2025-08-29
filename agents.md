# Pricing Service - Agent Documentation

## Overview

This is a FastAPI-based pricing service that scrapes and serves AI model pricing information from various providers. The service aggregates pricing data from multiple sources and provides both API endpoints and a web UI.

## Project Structure

```
lando-pricemaster/
├── src/pricing_service/
│   ├── __init__.py          # Package initialization
│   ├── scraper.py           # Main scraper orchestrator
│   ├── server.py            # FastAPI server
│   └── scrapers/            # Individual scraper modules
│       ├── __init__.py
│       ├── openai.py        # OpenAI pricing scraper
│       └── fal.py           # Fal.ai pricing scraper
├── data/
│   └── model_pricing.json   # Cached pricing data
├── ui/
│   └── index.html           # Web UI
├── pyproject.toml           # Python project configuration
├── Dockerfile               # Container configuration
└── README.md               # Basic usage instructions
```

## Key Components

### 1. Scraper System (`scraper.py`)

**Purpose**: Orchestrates multiple scraper modules to collect pricing data.

**Key Functions**:
- `run_scrapers()`: Executes all registered scraper modules
- `write_pricing_file(path)`: Saves aggregated data to JSON file

**Scraper Modules**: Located in `src/pricing_service/scrapers/`
- Each module must implement a `fetch_prices()` function
- Returns a dictionary with model IDs as keys
- Expected format: `{model_id: {"raw": data, "source": url}}`

### 2. FastAPI Server (`server.py`)

**Purpose**: Provides REST API and serves web UI.

**Endpoints**:
- `GET /` → Redirects to `/ui/`
- `GET /api/pricing` → Returns all pricing data
- `GET /api/pricing/{model_id}` → Returns specific model pricing
- `GET /ui/` → Serves web interface

**Features**:
- Automatic data refresh every 6 hours
- CORS enabled for cross-origin requests
- Static file serving for UI

### 3. Web UI (`ui/index.html`)

**Purpose**: User-friendly interface for viewing pricing data.

**Features**:
- Responsive grid layout
- Real-time data refresh
- Error handling and loading states
- Modern Material Design styling

## Development Workflow

### Setting Up Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -e .
```

### Running the Service

```bash
# Development mode with auto-reload
uvicorn pricing_service.server:app --host 0.0.0.0 --port 8001 --reload

# Production mode
python -m pricing_service.server
```

### Testing Individual Components

```bash
# Test scraper functionality
python -m pricing_service.scraper

# Test API endpoints
curl http://localhost:8001/api/pricing
curl http://localhost:8001/api/pricing/gpt-4

# Test UI
# Open http://localhost:8001/ui/ in browser
```

## Adding New Scrapers

### 1. Create Scraper Module

Create a new file in `src/pricing_service/scrapers/`:

```python
"""Scraper for [Provider Name] pricing."""
from __future__ import annotations
import requests
from bs4 import BeautifulSoup

PROVIDER_URL = "https://provider.com/pricing"

def fetch_prices() -> dict:
    """Fetch pricing data from provider."""
    try:
        response = requests.get(PROVIDER_URL, timeout=10)
        response.raise_for_status()
        
        # Parse HTML/JSON response
        # Extract pricing information
        
        data = {}
        # Add models to data dictionary
        # Format: {model_id: {"raw": pricing_data, "source": PROVIDER_URL}}
        
        return data
    except Exception as e:
        print(f"Error fetching {PROVIDER_URL}: {e}")
        return {}
```

### 2. Register Scraper

Add the new module to `SCRAPER_MODULES` in `scraper.py`:

```python
SCRAPER_MODULES: Iterable[str] = [
    "pricing_service.scrapers.openai",
    "pricing_service.scrapers.fal",
    "pricing_service.scrapers.new_provider",  # Add this line
]
```

## API Reference

### GET /api/pricing

Returns all available pricing data.

**Response Format**:
```json
{
  "gpt-4": {
    "raw": {
      "Model": "GPT-4",
      "Input": "$0.03/1K tokens",
      "Output": "$0.06/1K tokens"
    },
    "source": "https://openai.com/pricing"
  },
  "claude-3": {
    "raw": {
      "Model": "Claude 3",
      "Input": "$0.015/1K tokens",
      "Output": "$0.075/1K tokens"
    },
    "source": "https://anthropic.com/pricing"
  }
}
```

### GET /api/pricing/{model_id}

Returns pricing for a specific model.

**Parameters**:
- `model_id` (string): The model identifier

**Response**: Single model pricing object or 404 if not found

## Data Flow

1. **Startup**: Server loads existing data from `data/model_pricing.json`
2. **Background Refresh**: Every 6 hours, scrapers run and update the cache
3. **API Requests**: Serve cached data to clients
4. **UI Updates**: Frontend fetches data via API and displays it

## Error Handling

### Scraper Errors
- Individual scraper failures don't crash the system
- Failed scrapers are logged but don't prevent other scrapers from running
- Empty results are handled gracefully

### API Errors
- 404: Model not found
- 503: Pricing cache not ready (during startup)

### UI Errors
- Network errors are displayed to users
- Loading states provide feedback
- Graceful degradation when data is unavailable

## Configuration

### Environment Variables
- `REFRESH_INTERVAL`: Background refresh interval (default: 6 hours)
- `DATA_PATH`: Path to pricing data file
- `PORT`: Server port (default: 8000)

### File Paths
- Pricing data: `data/model_pricing.json`
- UI files: `ui/`
- Logs: Console output (can be redirected)

## Deployment

### Docker
```bash
# Build image
docker build -t pricing-service .

# Run container
docker run -p 8000:8000 pricing-service
```

### Production Considerations
- Use reverse proxy (nginx) for static files
- Implement proper logging
- Add health check endpoints
- Consider rate limiting for scrapers
- Use environment variables for configuration

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change port in uvicorn command
2. **Scraper failures**: Check network connectivity and website changes
3. **Import errors**: Ensure virtual environment is activated
4. **Path issues**: Verify file paths are correct for your OS

### Debug Mode
```bash
# Enable debug logging
uvicorn pricing_service.server:app --log-level debug
```

## Contributing

When modifying this service:

1. **Add scrapers**: Follow the established pattern
2. **Update UI**: Maintain responsive design
3. **Test thoroughly**: Verify all endpoints work
4. **Document changes**: Update this file and README.md

## Security Considerations

- CORS is enabled for all origins (configure appropriately for production)
- No authentication currently implemented
- Scrapers may be rate-limited by target sites
- Consider implementing API key authentication for production use
