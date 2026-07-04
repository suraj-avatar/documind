"""
routes.py — All API routes assembled into a single APIRouter.

Endpoints:
  GET  /health            — liveness + vectorstore stats
  POST /ask               — ask a question against ingested documents
  POST /upload            — upload PDF files for ingestion
  GET  /debug/retrieval   — inspect what chunks a query retrieves
"""

import time

from fastapi import APIRouter
from pydantic import BaseModel

from llm.rag_chain import generate_answer
from retrieval.hybrid_retriever import hybrid_search, _get_vectorstore
from api.upload import router as upload_router

router = APIRouter()

# Include upload sub-router
router.include_router(upload_router, tags=["Documents"])


# ── Request / Response models ────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    session_id: str = "default"


class QuestionResponse(BaseModel):
    answer: str
    sources: list[dict]


# ── Routes ───────────────────────────────────────────────────

@router.get("/health", summary="Health check", tags=["System"])
def health():
    """Returns API status and vectorstore document count."""
    try:
        vs = _get_vectorstore()
        doc_count = vs._collection.count()
    except Exception:
        doc_count = -1

    return {
        "status": "ok",
        "vectorstore_chunks": doc_count,
        "embedding_model": "BAAI/bge-base-en-v1.5",
        "llm_model": "llama-3.1-8b-instant",
    }


@router.post("/ask", response_model=QuestionResponse, summary="Ask a question", tags=["RAG"])
def ask_question(request: QuestionRequest):
    """
    Ask a question against the ingested documents.
    Optionally pass a `session_id` to retain conversation history.
    """
    start = time.time()

    response = generate_answer(
        request.question,
        session_id=request.session_id
    )

    latency = time.time() - start
    print(f"[ask] Latency={latency:.2f}s | session={request.session_id}")

    return {
        "answer": response["answer"],
        "sources": response["sources"],
    }


@router.get("/debug/retrieval", summary="Debug retrieval", tags=["Debug"])
def debug_retrieval(q: str):
    """Inspect exactly which chunks are retrieved for a given query."""
    results = hybrid_search(q)
    return {
        "query": q,
        "num_chunks_retrieved": len(results),
        "chunks": [
            {
                "rank": i + 1,
                "score": float(score),
                "source": chunk["metadata"].get("source", "unknown"),
                "page": chunk["metadata"].get("page", "?"),
                "preview": chunk["text"][:300],
            }
            for i, (chunk, score) in enumerate(results)
        ],
    }