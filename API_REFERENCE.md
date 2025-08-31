# Pricing Service API Reference

## Base URL
```
http://localhost:8001
```

## Authentication
Currently, no authentication is required. All endpoints are publicly accessible.

## Endpoints

### 1. Root Redirect
**GET** `/`

Redirects to the web UI.

**Response:**
- **Status:** 302 Found
- **Location:** `/ui/`

**Example:**
```bash
curl -I http://localhost:8001/
```

### 2. Get All Pricing Data
**GET** `/api/pricing`

Returns all available pricing data from all scrapers. Supports optional filtering by service type.

**Query Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `service_type` | string | Filter results by service type (e.g. `api_endpoint`, `server_rental`, `subscription`) |

**Response:**
- **Status:** 200 OK
- **Content-Type:** `application/json`

**Response Body:**
```json
{
  "gpt-4": {
    "raw": {
      "Model": "GPT-4",
      "Input": "$0.03/1K tokens",
      "Output": "$0.06/1K tokens",
      "Context": "8K tokens"
    },
    "source": "https://openai.com/pricing",
    "api_identifier": "openai",
    "service_type": "api_endpoint",
    "api_schema": null,
    "generation_latency": null,
    "description": null,
    "last_updated": "2024-01-01T00:00:00"
  },
  "gpt-3.5-turbo": {
    "raw": {
      "Model": "GPT-3.5 Turbo",
      "Input": "$0.0015/1K tokens",
      "Output": "$0.002/1K tokens",
      "Context": "4K tokens"
    },
    "source": "https://openai.com/pricing",
    "api_identifier": "openai",
    "service_type": "api_endpoint",
    "api_schema": null,
    "generation_latency": null,
    "description": null,
    "last_updated": "2024-01-01T00:00:00"
  }
}
```

**Example:**
```bash
# All services
curl http://localhost:8001/api/pricing

# Only API endpoints
curl http://localhost:8001/api/pricing?service_type=api_endpoint
```

**Empty Response (when no data available):**
```json
{}
```

### 3. Get Specific Model Pricing
**GET** `/api/pricing/{model_id}`

Returns pricing information for a specific model.

**Parameters:**
- `model_id` (string, required): The model identifier (e.g., "gpt-4", "claude-3")

**Response:**
- **Status:** 200 OK (if found)
- **Status:** 404 Not Found (if model doesn't exist)
- **Status:** 503 Service Unavailable (if cache not ready)
- **Content-Type:** `application/json`

**Success Response Body:**
```json
{
  "raw": {
    "Model": "GPT-4",
    "Input": "$0.03/1K tokens",
    "Output": "$0.06/1K tokens",
    "Context": "8K tokens"
  },
  "source": "https://openai.com/pricing",
  "api_identifier": "openai",
  "service_type": "api_endpoint",
  "api_schema": null,
  "generation_latency": null,
  "description": null,
  "last_updated": "2024-01-01T00:00:00"
}
```

**404 Response Body:**
```json
{
  "detail": "Model not found"
}
```

**503 Response Body:**
```json
{
  "detail": "Pricing cache not ready"
}
```

**Examples:**
```bash
# Get GPT-4 pricing
curl http://localhost:8001/api/pricing/gpt-4

# Get non-existent model
curl http://localhost:8001/api/pricing/non-existent-model
```

### 4. Web UI
**GET** `/ui/`

Serves the web interface for viewing pricing data.

**Response:**
- **Status:** 200 OK
- **Content-Type:** `text/html`

**Features:**
- Responsive grid layout
- Real-time data refresh
- Error handling
- Modern Material Design

**Example:**
```bash
curl http://localhost:8001/ui/
```

## Data Structure

### Pricing Object Format
Each model in the pricing data follows this structure:

```json
{
  "model_id": {
    "raw": {
      // Raw pricing data from scraper
      // Structure varies by provider
      "Model": "Model Name",
      "Input": "Input pricing",
      "Output": "Output pricing",
      // ... other fields
    },
    "source": "https://provider.com/pricing",
    "api_identifier": "provider",
    "service_type": "api_endpoint",
    "api_schema": null,
    "generation_latency": null,
    "description": null,
    "last_updated": "2024-01-01T00:00:00"
  }
}
```

### Common Pricing Fields
While the exact structure varies by provider, common fields include:

- `api_identifier`: Provider's API identifier
- `service_type`: Classification of the entry (`api_endpoint`, `server_rental`, `subscription`, etc.)
- `api_schema`: JSON schema or usage snippet for the model's API (if available)
- `generation_latency`: Typical time to generate a result (if available)
- `description`: Human-readable model description when provided
- `last_updated`: ISO timestamp for when the record was scraped
- `Model`: Model name/identifier
- `Input`: Input token pricing
- `Output`: Output token pricing
- `Context`: Context window size
- `Training`: Training data cutoff
- `Availability`: Model availability status

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 302 | Redirect (root endpoint) |
| 404 | Model not found |
| 503 | Service unavailable (cache not ready) |

## Rate Limiting
Currently, no rate limiting is implemented. However, scrapers may be rate-limited by target websites.

## CORS
CORS is enabled for all origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Caching
- Data is cached in memory and refreshed every 6 hours
- Cache is initialized on server startup
- Failed scrapers don't affect cached data from successful scrapers

## Examples

### JavaScript/Fetch API
```javascript
// Get all pricing data
const response = await fetch('http://localhost:8001/api/pricing');
const data = await response.json();

// Get specific model
const modelResponse = await fetch('http://localhost:8001/api/pricing/gpt-4');
const modelData = await modelResponse.json();
```

### Python/Requests
```python
import requests

# Get all pricing data
response = requests.get('http://localhost:8001/api/pricing')
data = response.json()

# Get specific model
model_response = requests.get('http://localhost:8001/api/pricing/gpt-4')
model_data = model_response.json()
```

### cURL
```bash
# Get all pricing
curl -X GET http://localhost:8001/api/pricing

# Get specific model
curl -X GET http://localhost:8001/api/pricing/gpt-4

# Pretty print JSON
curl -X GET http://localhost:8001/api/pricing | python -m json.tool
```

## Health Check
While not explicitly implemented, you can use the `/api/pricing` endpoint as a health check:
- 200 response indicates the service is running
- Empty JSON `{}` is a valid response when no data is available
