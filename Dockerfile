FROM python:3.11-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering — logs appear instantly
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS-level deps for torch / sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
# CPU-only torch first (saves ~1.5GB vs CUDA build)
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Create empty directories for the vectorstore and document store.
# These are populated at runtime via the POST /upload endpoint.
# In production, mount a Railway volume at /app/vectorstore and
# /app/parent_store so data persists across deploys.
RUN mkdir -p /app/vectorstore /app/parent_store

# Health check — Railway marks the container unhealthy if /health fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Single worker — appropriate for 1 GB RAM free-tier deployment
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]