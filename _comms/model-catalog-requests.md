Subject: Requests to finalize and optimize Script2Screen integration

Team,

Thank you for aligning your catalog API with our needs. Below are concrete requests and nice‑to‑haves that will make discovery and add‑model UX robust and low‑maintenance on our side.

Core contract (discovery)
- Endpoint: `GET /api/pricing`
  - Support filters (already implemented):
    - `service_type=api_endpoint` → only generation models (we default to this)
    - `provider=<code>` → limit to a provider (e.g., `fal`, `runway`, `hedra`, `openai`, `elevenlabs`, `gemini`)
  - Payload shapes supported by us:
    - Dict: `{ "Display Name": { ...metadata } }`
    - List: `[ { model_id, display? } ]`
- Required fields per entry (Dict shape):
  - `modalities: string[]` (e.g., ["text-to-video", "image-to-video"]) — used to map to our internal modality keys
  - `api_identifier: string` (provider code: `fal`, `runway`, `hedra`, `openai`, `elevenlabs`, `gemini`)
  - `display: string` (human‑readable pricing like `$0.05 / second`)
  - `description: string` (non‑null; empty string is fine)
  - `service_type: "api_endpoint" | "server_rental" | ...` (we filter to `api_endpoint`)
  - `last_updated: ISO string` (for freshness)
  - `source: string` (URL to original pricing page)
- Optional but very helpful:
  - `api_schema: object | string (openapi_url)` — for parameter UI; if a URL, we’ll fetch
  - `generation_latency: string | number` — relative or numeric hints
  - `price`, `unit`, `currency` — in addition to `display` (for programmatic display)

Model identity
- If possible, include a canonical `model_id` field (provider‑qualified), even in Dict shape entries:
  - Examples: `fal-ai/veo3`, `runway/gen4/t2v`, `hedra/character-3/image-to-video`, `eleven_v3`
  - We can still build IDs from `api_identifier + slug(name)`, but a canonical `model_id` avoids heuristics and edge cases.

Modality mapping (we already support these)
- text-to-image → image_model
- image-to-image → image_edit_model
- inpainting → image_inpaint_model
- background-removal → bg_removal_model
- segmentation → segmentation_model
- outpainting → image_outpaint_model
- text-to-video → video_model
- image-to-video → video_edit_model
- video-to-video → video_to_video_model
- video-upscaling → video_upscale_model
- video-background-removal → video_bg_removal_model
- dialogue-video (+ single-speaker|multi-speaker) → dialogue_video_model | dialogue_video_multi_model
- lipsync → lipsync_model
- extend | video-extension → video_extend_model
- Audio: tts → dialogue_model; sts|voice-changer → voice_to_voice_model; music → music_model; sound-effects → sfx_model

Additional metadata that would improve UX (nice‑to‑have)
- `recommended_use: string` — short guidance we can show in tooltips
- `quality_tier: string` — e.g., basic/standard/premium
- `constraints`: object (e.g., `max_duration_seconds`, `supported_resolutions`, `fps`, `max_batch`)
- `capabilities: string[]` — extra capability tags we can surface as badges
- `policy_notes: string` — usage constraints we can show in UI

Operational endpoints
- `GET /api/health` → `{ status: "ok", version, updated, cache_size }` (done)
- `POST /api/refresh` → non‑blocking refresh trigger (done)

Bulk/offline
- Provide/update `data/model_pricing.json` — we set `MODEL_PRICING_URL=file:///...` for offline dev and CI.

Stability and performance
- Continue returning non‑null `description` (we hit a null earlier; we now guard it, but non‑null avoids noisy logs).
- Keep service_type accurate (`api_endpoint` vs `server_rental`) so our discovery stays clean.
- Caching and <2s response time are great; thank you for implementing this.

Testing bundle request
- Please share a small sample (20–30 entries) across providers with `service_type=api_endpoint` that includes the fields above, so we can fixture our UI.

Current state on our side
- We now default discovery to `?service_type=api_endpoint` and fall back to unfiltered only if needed.
- We display pricing from `display` and also show a few `capabilities` lines (we add `display` there too for visibility).
- We added a user‑facing modality picker (pre‑filled with your `modalities`) when adding models; users can override categories.

Thank you for the quick turnaround and for exposing filters and health/refresh. If you add `api_schema` (object or URL) per model in the future, we’ll immediately begin rendering richer parameter UIs without extra work on your side.

