FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies first (for better caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY src ./src
COPY data ./data
COPY ui ./ui
COPY assets ./assets

# Copy startup script
COPY start_server.py /start_server.py
RUN chmod +x /start_server.py

# Ensure the package is properly installed
RUN pip install --no-cache-dir -e .

# Cloud Run sets PORT env var automatically, default to 8080
ENV PORT=8080
EXPOSE 8080

# Use Python script to read PORT from environment and start uvicorn
CMD ["python", "/start_server.py"]
