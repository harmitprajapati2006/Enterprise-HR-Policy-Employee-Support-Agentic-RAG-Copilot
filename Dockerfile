# Use lightweight official Python runtime
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Set work directory
WORKDIR /app

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY app/ ./app/
COPY data/ ./data/
COPY static/ ./static/
COPY templates/ ./templates/
COPY ingest_sample_kb.py .
COPY run.py .

# Create uploads directory and audit storage directory
RUN mkdir -p /app/uploads /app/data/sample_kb

# Expose server port
EXPOSE 8000

# Health check to ensure FastAPI is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start the enterprise copilot web server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
