# AI Model Pricing Service - API Reference

## Overview

The AI Model Pricing Service provides REST API endpoints for accessing AI model pricing data, metadata, and change tracking. The service aggregates pricing information from multiple providers and offers both dictionary-based and list-based data formats.

**Base URL**: `http://localhost:8001` (default)

## Authentication

Currently no authentication is required. All endpoints are publicly accessible.

## Data Models

### Model Record Structure

All model records contain the following fields:

```json
{
  "name": "string",                    // Display name of the model
  "model_id": "string",               // Canonical model identifier
  "provider": "string",               // Provider code (e.g., "fal", "openai")
  "service_type": "string",           // Type of service (e.g., "api_endpoint", "server_rental")
  "modalities": ["string"],           // Array of supported modalities
  "display": "string",                // Human-readable price display
  "price": "number",                  // Numeric price value
  "unit": "string",                   // Price unit (e.g., "per_1k_tokens", "per_hour")
  "currency": "string",               // Currency code (e.g., "USD")
  "description": "string",            // Model description
  "source": "string",                 // Source URL for pricing data
  "last_updated": "string",           // ISO timestamp of last update
  "first_seen": "string",             // ISO timestamp when first discovered
  "last_changed": "string",           // ISO timestamp of last data change
  "status": "string",                 // Model status: "active" or "deprecated"
  "change_count": "number",           // Number of times data has changed
  "generation_latency": "string",     // Expected generation latency
  "recommended_use": "string",        // Recommended use case
  "quality_tier": "string",           // Quality tier (e.g., "premium", "standard")
  "constraints": "object",            // Usage constraints and limits
  "capabilities": ["string"],         // Array of model capabilities
  "policy_notes": "string",           // Policy and usage notes
  "api_schema": "object",             // JSON schema for API parameters
  "thumbnail_url": "string",          // URL to model thumbnail/preview image
  "sample_outputs": ["string"],       // Array of sample output image URLs
  "demo_video": "string",             // URL to demo video (if available)
  "raw": "object"                     // Raw pricing data from source
}
```

## Endpoints

### 1. Root Redirect

**GET** `/`

Redirects to the web UI at `/ui/`.

**Response**: 302 Redirect to `/ui/`

---

### 2. Get All Pricing Data

**GET** `/api/pricing`

Returns pricing data for all models in dictionary format, keyed by model name.

**Query Parameters**:
- `service_type` (optional): Filter by service type (e.g., "api_endpoint", "server_rental")
- `provider` (optional): Filter by provider code (e.g., "fal", "openai", "runway")
- `modality` (optional): Filter by modality (e.g., "text-to-video")

**Response**: `Dict[str, dict]`
```json
{
  "gpt-4": {
    "model_id": "openai/gpt-4",
    "provider": "openai",
    "service_type": "api_endpoint",
    "modalities": ["text-generation"],
    "display": "$0.03/1K tokens",
    "price": 0.03,
    "unit": "per_1k_tokens",
    "currency": "USD",
    "status": "active",
    "first_seen": "2025-01-01T00:00:00",
    "last_updated": "2025-01-15T12:00:00",
    // ... other fields
  }
}
```

**Error Responses**:
- `503`: Pricing cache not ready (during startup)

---

### 3. Get Specific Model Pricing

**GET** `/api/pricing/{model_id}`

Returns pricing data for a specific model.

**Path Parameters**:
- `model_id` (string): The model identifier

**Response**: `dict` - Single model record

**Error Responses**:
- `404`: Model not found
- `503`: Pricing cache not ready

---

### 4. List Models (Array Format)

**GET** `/api/models`

Returns models in array format for clients that prefer list responses.

**Query Parameters**:
- `service_type` (optional): Filter by service type
- `provider` (optional): Filter by provider code
- `modality` (optional): Filter by modality

**Response**: `List[dict]` - Array of model records

---

### 5. List Providers

**GET** `/api/providers`

Returns summary statistics for all providers.

**Response**: `List[dict]`
```json
[
  {
    "provider": "openai",
    "model_count": 15,
    "service_types": ["api_endpoint"],
    "modalities": ["text-generation", "text-to-speech"],
    "last_updated": "2025-01-15T12:00:00"
  }
]
```

---

### 6. List Modalities

**GET** `/api/modalities`

Returns modalities with associated model counts and providers.

**Response**: `List[dict]`
```json
[
  {
    "modality": "text-to-video",
    "model_count": 25,
    "providers": ["runway", "fal"],
    "service_types": ["api_endpoint"]
  }
]
```

---

### 7. Health Check

**GET** `/api/health`

Returns service health and status information.

**Response**: `dict`
```json
{
  "status": "ok",
  "version": "1.0.0",
  "updated": "2025-01-15T12:00:00",
  "cache_size": 567
}
```

---

### 8. Get Recent Changes

**GET** `/api/changes`

Returns summary of recent changes (new, changed, deprecated models).

**Response**: `dict`
```json
{
  "new_models": ["model1", "model2"],
  "changed_models": ["model3"],
  "deprecated_models": ["model4"],
  "update_timestamp": "2025-01-15T12:00:00"
}
```

**Alternative Response** (when no recent changes):
```json
{
  "message": "No recent changes available",
  "last_update": "2025-01-15T12:00:00"
}
```

---

### 9. Get New Models

**GET** `/api/models/new`

Returns recently added models.

**Query Parameters**:
- `days` (optional, default: 7): Number of days to look back for new models
- `limit` (optional, default: 50): Maximum number of models to return

**Response**: `List[dict]` - Array of model records, sorted by first_seen date (newest first)

**Error Responses**:
- `503`: Pricing cache not ready

---

### 10. Get Changed Models

**GET** `/api/models/changed`

Returns recently changed models.

**Query Parameters**:
- `days` (optional, default: 7): Number of days to look back for changed models
- `limit` (optional, default: 50): Maximum number of models to return

**Response**: `List[dict]` - Array of model records with `change_count` field, sorted by last_changed date (most recent first)

**Error Responses**:
- `503`: Pricing cache not ready

---

### 11. Get Deprecated Models

**GET** `/api/models/deprecated`

Returns recently deprecated models.

**Query Parameters**:
- `days` (optional, default: 30): Number of days to look back for deprecated models
- `limit` (optional, default: 50): Maximum number of models to return

**Response**: `List[dict]` - Array of model records with `deprecated_at` field, sorted by deprecated_at date (most recent first)

**Error Responses**:
- `503`: Pricing cache not ready

---

### 12. Get Model Thumbnail

**GET** `/api/thumbnail/{model_id}`

Returns the thumbnail image for a specific model.

**Path Parameters**:
- `model_id` (string): The model identifier

**Response**: Image file (JPEG, PNG, etc.)

**Error Responses**:
- `404`: Model not found or no thumbnail available
- `502`: Failed to fetch thumbnail from source
- `503`: Pricing cache not ready

**Headers**:
- `Cache-Control`: `public, max-age=3600` (cached for 1 hour)
- `Access-Control-Allow-Origin`: `*`

---

### 13. Trigger Refresh

**POST** `/api/refresh`

Triggers a background refresh of pricing data.

**Response**: `dict`
```json
{
  "status": "refresh_triggered",
  "message": "Pricing data refresh started in background"
}
```

**Alternative Response** (when refresh already running):
```json
{
  "status": "refresh_pending",
  "message": "A refresh is already running"
}
```

---

## Error Handling

### HTTP Status Codes

- `200`: Success
- `302`: Redirect (root endpoint)
- `404`: Model not found
- `503`: Service unavailable (cache not ready)

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

## Data Refresh Behavior

- **Automatic Refresh**: Data is automatically refreshed every 6 hours
- **Incremental Updates**: Only changed models are updated, preserving existing data
- **Change Tracking**: All changes are tracked with timestamps and change counts
- **Background Processing**: Refreshes run in background without blocking API access

## CORS Support

All endpoints support CORS with the following configuration:
- `allow_origins`: `["*"]` (all origins)
- `allow_credentials`: `true`
- `allow_methods`: `["*"]` (all methods)
- `allow_headers`: `["*"]` (all headers)

## Rate Limiting

Currently no rate limiting is implemented. Consider implementing rate limiting for production deployments.

## Examples

### Get all OpenAI models
```bash
curl "http://localhost:8001/api/models?provider=openai"
```

### Get new models from last 3 days
```bash
curl "http://localhost:8001/api/models/new?days=3&limit=10"
```

### Get text-to-video models
```bash
curl "http://localhost:8001/api/models?modality=text-to-video"
```

### Trigger manual refresh
```bash
curl -X POST "http://localhost:8001/api/refresh"
```

### Get specific model details
```bash
curl "http://localhost:8001/api/pricing/gpt-4"
```

### Get model thumbnail
```bash
curl "http://localhost:8001/api/thumbnail/gpt-4" -o thumbnail.jpg
```

### Get models with thumbnails
```bash
curl "http://localhost:8001/api/models" | jq '.[] | select(.thumbnail_url != null)'
```
