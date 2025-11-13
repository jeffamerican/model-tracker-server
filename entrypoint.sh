#!/bin/bash
set -e

# Entrypoint script for Cloud Run
# Reads PORT from environment (set by Cloud Run) and starts uvicorn

PORT=${PORT:-8080}
echo "Starting server on port ${PORT}..."
exec uvicorn pricing_service.server:app --host 0.0.0.0 --port "${PORT}"

