# Catalog Schema Feedback – Seedance models

Thanks for exposing `api_schema` in `/api/pricing`. After importing `fal-ai/fal-ai/bytedance/seedance/v1/pro/text-to-video`, Script2Screen persists the schema payload exactly as received. Right now the catalog is returning an example invocation body:

```json
{
  "seed": 42,
  "video": {
    "url": "https://storage.googleapis.com/falserverless/example_inputs/seedance_pro_t2v.mp4"
  }
}
```

Our UI expects a parameter *schema* (field metadata), not a sample request. We translate schemas that follow either of these formats:

1. **Flat fields map (preferred)**

```json
{
  "prompt": {
    "type": "string",
    "title": "Prompt",
    "description": "Text description of the video to generate",
    "required": true
  },
  "seed": {
    "type": "integer",
    "title": "Seed",
    "default": 42
  },
  "video_url": {
    "type": "string",
    "title": "Reference video URL",
    "format": "uri"
  }
}
```

2. **OpenAPI fragment** (object with `openapi`, `paths`, etc.); we convert to the same fields map internally.

If you already have OpenAPI for the Seedance endpoints, you can embed it under `api_schema`. Otherwise please supply a fields map describing the supported parameters, types, defaults, enums, etc. Without that metadata, we can’t render advanced controls, so the backend treats the model as “missing schema”.

Once the payload includes real schema data, imports will succeed *and* the UI will surface the proper controls automatically. Let us know if you have a sample we can test against.
