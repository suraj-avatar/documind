"""
ingest.py — Document ingestion pipeline.

Provides a callable `ingest_documents(file_paths)` function so it can be
invoked programmatically from the upload API endpoint, as well as a CLI
entry point for bulk ingestion of a directory.
"""

import os
import time

from dotenv import load_dotenv
load_dotenv()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.storage import LocalFileStore
from langchain_classic.storage._lc_store import create_kv_docstore
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ── Project-root-relative paths ──────────────────────────────
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

VECTORSTORE_PATH = os.path.join(_PROJECT_ROOT, "vectorstore")
PARENT_STORE_PATH = os.path.join(_PROJECT_ROOT, "parent_store")
BM25_CACHE_PATH = os.path.join(_PROJECT_ROOT, "bm25_cache.pkl")


def ingest_documents(file_paths: list[str]) -> dict:
    """
    Ingest a list of PDF file paths into the shared vectorstore.

    Args:
        file_paths: Absolute paths to PDF files to ingest.

    Returns:
        dict with keys: files_ingested, chunks_added
    """
    if not file_paths:
        return {"files_ingested": 0, "chunks_added": 0}

    # ── 1. Load documents ────────────────────────────────────
    all_docs = []
    for path in file_paths:
        try:
            loader = PyPDFLoader(path)
            docs = loader.load()
            # Tag each page with just the filename as doc_type (generic)
            for doc in docs:
                doc.metadata["doc_type"] = os.path.splitext(
                    os.path.basename(path)
                )[0]
            all_docs.extend(docs)
            print(f"[ingest] Loaded {len(docs)} pages from {os.path.basename(path)}")
        except Exception as e:
            print(f"[ingest] ERROR loading {path}: {e}")

    if not all_docs:
        return {"files_ingested": 0, "chunks_added": 0}

    # ── 2. Splitters ─────────────────────────────────────────
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
    )

    # ── 3. Embedding model ───────────────────────────────────
    print("[ingest] Loading embedding model...")
    start = time.time()
    embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")
    print(f"[ingest] Embedding model ready in {time.time() - start:.2f}s")

    # ── 4. Vectorstore ───────────────────────────────────────
    vectorstore = Chroma(
        collection_name="child_chunks",
        embedding_function=embedding,
        persist_directory=VECTORSTORE_PATH,
    )

    # ── 5. Parent docstore ───────────────────────────────────
    store = LocalFileStore(PARENT_STORE_PATH)
    docstore = create_kv_docstore(store)

    # ── 6. Retriever + ingest ────────────────────────────────
    retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=docstore,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )

    before_count = vectorstore._collection.count()
    retriever.add_documents(all_docs)
    after_count = vectorstore._collection.count()
    chunks_added = after_count - before_count

    # ── 7. Invalidate BM25 cache ─────────────────────────────
    if os.path.exists(BM25_CACHE_PATH):
        os.remove(BM25_CACHE_PATH)
        print("[ingest] BM25 cache cleared — will rebuild on next query")

    print(f"[ingest] Done. {len(file_paths)} file(s), {chunks_added} child chunks added.")
    return {
        "files_ingested": len(file_paths),
        "chunks_added": chunks_added,
    }


# ── CLI entry point ──────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import glob

    if len(sys.argv) < 2:
        print("Usage: python ingest.py <directory_or_glob>")
        sys.exit(1)

    pattern = sys.argv[1]
    if os.path.isdir(pattern):
        paths = glob.glob(os.path.join(pattern, "**/*.pdf"), recursive=True)
    else:
        paths = glob.glob(pattern, recursive=True)

    if not paths:
        print(f"No PDF files found matching: {pattern}")
        sys.exit(1)

    print(f"Found {len(paths)} PDF file(s) to ingest.")
    result = ingest_documents(paths)
    print(f"Result: {result}")