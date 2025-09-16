**Purpose**
- Align the Script2Screen discovery endpoint with your model-catalog server so users can discover, add, and categorize models reliably.
- Ensure the catalog payload has the fields our backend uses for classification, pricing, and schema.

**Current Integration Summary**
- Our backend (FastAPI) calls your server at `http://localhost:8001/api/pricing` during discovery.
- We accept two payload shapes:
  - Dict shape: top-level object keyed by human display name with metadata as value.
  - List shape: array of records with at least `model_id` (+ optional pricing/display fields).
- We normalize and classify models into internal modalities and surface them in the UI for users to add with an editable modality picker.

**Required Endpoint**
- `GET /api/pricing`
  - Must be accessible from the backend host (CORS not needed for server→server, but good hygiene for browser testing).
  - Response should be either the Dict or List shape (see below).
  - Please keep the endpoint responsive (<3–5s). If you must aggregate upstream APIs, consider caching.

**Optional Endpoints**
- `POST /api/refresh` (idempotent): trigger a background refresh of the catalog so we can call it from our UI (`/api/models/refresh-data`).
- `GET /api/health`: quick health signal.

**Payload Fields We Consume**
- Common (both shapes)
  - `modalities`: array of source modality strings. We map these into Script2Screen modalities.
  - `api_identifier`: a short key for provider/source (e.g., `fal`, `runway`, `hedra`, `openai`).
  - `display`: human-friendly price string when available (e.g., `$0.06 / image`).
  - `raw`: optional raw data. If it includes pricing under a key like `Price`/`price` we’ll surface it as a capability line.
  - `description`: short string description. Please avoid `null` (use empty string or omit).
  - `api_schema`: optional object or URL for the model’s parameter schema (OpenAPI subset or inferred schema). Either is helpful; we can fetch it if a URL.
  - `generation_latency`: optional relative latency hints.
  - `last_updated`: ISO string for data freshness.
  - `service_type`: please tag non-generation rows (e.g., `server_rental`) so we can ignore them by default.

**Dict Shape (Preferred When Rich Metadata Is Available)**
- Top-level object keyed by display name. Example (abbreviated):
```
{
  "Runway Gen4 T2V": {
    "api_identifier": "runway",
    "modalities": ["text-to-video"],
    "display": "$0.05 / second",
    "raw": { "unit": "per_second", "amount": 0.05 },
    "api_schema": { ... } | "https://.../openapi.json",
    "generation_latency": "fast",
    "description": "Text-to-video generation",
    "last_updated": "2025-09-15T21:20:00Z",
    "service_type": "api_endpoint"
  }
}
```

**List Shape (Minimum)**
- Each record must include a stable `model_id`. Optional pricing metadata helps ranking.
```
[
  { "model_id": "fal-ai/flux/dev", "display": "$0.04 / image" },
  { "model_id": "runway/gen4/t2v", "display": "$0.05 / second" }
]
```

**Model ID Expectations**
- If your data starts with product names vs. provider IDs, include enough fields so we can construct a provider-qualified ID.
  - We currently default unknown items to `fal-ai/<slug>` as a heuristic; supplying `api_identifier` + unambiguous name avoids bad guesses.
  - Best: include a canonical `model_id` in provider namespace already, e.g. `fal-ai/veo3`, `runway/gen4/t2v`, `hedra/character-3/image-to-video`.

**Modality Mapping**
- We convert your `modalities` to our internal keys:
  - `text-to-image` → `image_model`
  - `image-to-image` (img2img/edit) → `image_edit_model`
  - `inpainting` → `image_inpaint_model`
  - `background-removal` → `bg_removal_model`
  - `segmentation` → `segmentation_model`
  - `outpainting` → `image_outpaint_model`
  - `text-to-video` → `video_model`
  - `image-to-video` → `video_edit_model`
  - `video-to-video` → `video_to_video_model`
  - `video-upscaling` → `video_upscale_model`
  - `video-background-removal` → `video_bg_removal_model`
  - `dialogue-video` (+ optional `single-speaker`|`multi-speaker`) → `dialogue_video_model` | `dialogue_video_multi_model`
  - `lipsync` → `lipsync_model`
  - `video-extension`/`extend` → `video_extend_model`
  - Audio:
    - `tts` → `dialogue_model`
    - `sts`/`voice-changer` → `voice_to_voice_model`
    - `music` → `music_model`
    - `sound-effects` → `sfx_model`

Please include clear modality strings (and synonyms acceptable). We do an additional client-side tag normalization for robustness, but explicit modalities improve accuracy.

**Pricing Fields**
- Provide any of the following you have; we prioritize `display` for UI:
  - `currency`: e.g., `USD`
  - `unit`: e.g., `per_image`, `per_second`, `per_request`
  - `price`: numeric unit price
  - `display`: formatted string (preferred for UI)
  - In `raw`, keep additional vendor fields; we’ll not render them unless useful.

**Schema Support (Optional But Helpful)**
- Either embed a lightweight schema in `api_schema` (parameters, types, enums) or provide an `openapi_url`.
- Even a minimal set helps us prefill recommended defaults when users add models.

**Filtering and Service Types**
- Please set `service_type` for rows like GPU rental so we can filter them out.
- Support query filtering if convenient:
  - `/api/pricing?service_type=api_endpoint`
  - `/api/pricing?provider=fal` (optional)

**Data Quality Expectations**
- `description`: avoid `null`. Use empty string `""` or omit the field.
- `api_identifier`: stable short code per provider; we use it to format model IDs and badges.
- `last_updated`: ISO string (optional, helps debugging freshness).

**Performance and Stability**
- Cache upstream calls on your side and serve from memory/disk to keep latency low and availability high.
- Keep your response size reasonable (we can stream or paginate later if needed).

**Health and Refresh**
- If possible, implement:
  - `GET /api/health` → `{ status: "ok", version: "...", updated: "..." }`
  - `POST /api/refresh` → triggers a refresh; return immediately.

**Example Good Dict Entry**
```
{
  "VEO 3": {
    "api_identifier": "fal",
    "modalities": ["text-to-video", "image-to-video"],
    "display": "$0.04 / second",
    "description": "High quality T2V/I2V",
    "last_updated": "2025-09-15T21:20:00Z",
    "service_type": "api_endpoint"
  }
}
```

**Open Questions / Requests**
- Can you provide a bulk export file (JSON) for offline development? If yes, we can set `MODEL_PRICING_URL=file:///path/to/file.json` on our side for local testing.
- If you have a stable canonical `model_id` format per provider, please share a mapping table so we avoid heuristics.
- If you have category tags beyond modalities (e.g., quality tiers, recommended use), we can surface those in cards.
- Would you prefer we filter non-generation services by default (e.g., `server_rental` rows)? If so, we’ll call `/api/pricing?service_type=api_endpoint`.

**Contacts**
- Script2Screen backend expects the above fields in `/api/pricing` and prefers a connected status at `/api/models/server-status` from our app.
- If you plan schema or field changes, please notify us in advance so we can keep discovery stable.

