# Request: Ensure schemas are exposed for discovery

Hi model‑catalog team,

Quick update on the Script2Screen Settings ➜ “Add Models” integration against your catalog server (port 8001).

**Status**
- We’ve patched the catalog so every fal.ai entry—Seedance included—now exposes a structured `api_schema` object directly in the top-level record. You should see the decoded JSON payload in `/api/pricing` responses.
- After pulling the latest data bundle, the UI no longer highlights these rows as “missing schema,” and the modal shows a preview of the new JSON structure.

**Remaining ask**
- Please retry the import flow on your side and confirm the backend accepts `fal-ai/fal-ai/bytedance/seedance/v1/pro/text-to-video` (and the other Seedance variants) now that the schema field is present.
- If anything still rejects these models, send back the request/response pair or log snippet so we can double-check parsing expectations.

Thanks!
