"""
upload.py — PDF upload and ingestion endpoint.

Accepts one or more PDF files via multipart form upload,
saves them to a temp directory, runs the ingestion pipeline,
then invalidates the in-memory retriever cache.
"""

import os
import tempfile
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from ingestion.ingest import ingest_documents
from retrieval.hybrid_retriever import reset_retrievers

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE_MB = 50


@router.post("/upload", summary="Upload PDF documents for ingestion")
async def upload_documents(files: list[UploadFile] = File(...)):
    """
    Upload one or more PDF files to be ingested into the RAG knowledge base.

    - Files are saved temporarily, ingested, then the temp copies are deleted.
    - The in-memory retriever cache is invalidated so the next query uses
      the freshly ingested data.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # Validate file types
    for f in files:
        if f.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"'{f.filename}' is not a PDF. Only PDF files are accepted."
            )

    temp_dir = tempfile.mkdtemp(prefix="rag_upload_")
    saved_paths = []

    try:
        # Save uploads to temp directory
        for upload in files:
            dest = os.path.join(temp_dir, upload.filename)
            with open(dest, "wb") as out:
                shutil.copyfileobj(upload.file, out)
            saved_paths.append(dest)
            print(f"[upload] Saved: {upload.filename} → {dest}")

        # Run ingestion pipeline
        result = ingest_documents(saved_paths)

        # Invalidate lazy-loaded retriever globals
        reset_retrievers()

        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "message": f"Successfully ingested {result['files_ingested']} file(s).",
                "files_ingested": result["files_ingested"],
                "chunks_added": result["chunks_added"],
                "filenames": [f.filename for f in files],
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )

    finally:
        # Always clean up temp files
        shutil.rmtree(temp_dir, ignore_errors=True)
