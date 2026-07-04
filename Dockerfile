FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── System deps ──────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ──────────────────────────────────────────────
# CPU-only torch first (saves ~1.5 GB vs CUDA build)
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ── Application source ───────────────────────────────────────
# Copies local app/ → /app/app/ inside the container
COPY app/ ./app/

# ── Runtime data directories ─────────────────────────────────
# Vectorstore and parent store are empty at build time.
# They are populated at runtime via POST /upload.
# Mount a Railway volume at /app/vectorstore for persistence.
RUN mkdir -p /app/vectorstore /app/parent_store

# ── Working directory for the server ─────────────────────────
# main.py uses flat imports (from api.routes import ..., from logger import ...)
# that only resolve when the CWD is /app/app (the package root).
WORKDIR /app/app

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]