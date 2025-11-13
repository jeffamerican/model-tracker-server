#!/usr/bin/env python3
"""Startup script for Cloud Run that reads PORT from environment."""
import os
import sys
import subprocess

# Get PORT from environment (Cloud Run sets this automatically)
port = os.environ.get("PORT", "8080")

print(f"Starting server on port {port}...")

# Start uvicorn with the port from environment
cmd = [
    "uvicorn",
    "pricing_service.server:app",
    "--host", "0.0.0.0",
    "--port", port
]

sys.exit(subprocess.run(cmd).returncode)

