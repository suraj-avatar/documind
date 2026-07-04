"""
main.py — FastAPI application entry point.

Configures:
  - CORS (required for the React frontend)
  - Request logging middleware
  - All API routes via the central router
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

from api.routes import router
from logger import logger

# ── App instance ─────────────────────────────────────────────
app = FastAPI(
    title="DocuMind RAG API",
    description=(
        "A production-grade Retrieval-Augmented Generation API. "
        "Upload any PDF documents and ask questions against them using "
        "hybrid semantic + keyword search with cross-encoder reranking."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow React frontend (any origin in dev, restrict in prod) ────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Lock this down to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    start = time.time()
    logger.info(f"[{req_id}] → {request.method} {request.url.path}")
    response = await call_next(request)
    latency = time.time() - start
    logger.info(f"[{req_id}] ← {response.status_code} ({latency:.2f}s)")
    return response


# ── Root ─────────────────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    return {
        "message": "DocuMind RAG API is running",
        "docs": "/docs",
        "health": "/health",
    }


# ── Include all routes ────────────────────────────────────────
app.include_router(router)