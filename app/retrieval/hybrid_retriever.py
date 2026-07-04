import os
import time
import pickle
import torch

# Resolve paths relative to the project root (two levels up from this file)
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from langchain_classic.storage import LocalFileStore
from langchain_classic.storage._lc_store import create_kv_docstore
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ------------------------
# FIX 5: Use all available CPU threads for torch inference
# ------------------------
torch.set_num_threads(os.cpu_count() or 4)

# ------------------------
# LAZY GLOBALS — loaded only once on first request (Fix 1 & 2)
# ------------------------
_embedding = None
_vectorstore = None
_docstore = None
_retriever = None
_bm25 = None
_documents = None
_metadatas = None
_reranker = None

BM25_CACHE_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    "bm25_cache.pkl"
)


def reset_retrievers():
    """
    Invalidate all lazy-loaded globals so they reload from disk on the next
    request. Call this after new documents are ingested via the upload API.
    """
    global _embedding, _vectorstore, _docstore, _retriever
    global _bm25, _documents, _metadatas, _reranker
    _vectorstore = None
    _docstore = None
    _retriever = None
    _bm25 = None
    _documents = None
    _metadatas = None
    # Keep _embedding and _reranker — model weights don't change on ingest
    print("[retriever] Lazy globals reset — will reload on next request")


def _get_embedding():
    """Lazy-load the embedding model (cached after first call)."""
    global _embedding
    if _embedding is None:
        print("===================================")
        print("Loading Embedding Model (first time only)...")
        print("===================================")
        start = time.time()
        _embedding = HuggingFaceEmbeddings(
            model_name="BAAI/bge-base-en-v1.5"
        )
        print(f"Embedding Model Loaded in {time.time() - start:.2f}s")
    return _embedding


def _get_vectorstore():
    """Lazy-load ChromaDB (cached after first call)."""
    global _vectorstore
    if _vectorstore is None:
        print("===================================")
        print("Opening Chroma (first time only)...")
        print("===================================")
        start = time.time()
        _vectorstore = Chroma(
            collection_name="child_chunks",
            embedding_function=_get_embedding(),
            persist_directory=os.path.join(_PROJECT_ROOT, "vectorstore")
        )
        print(f"Chroma Opened in {time.time() - start:.2f}s")
        try:
            count = _vectorstore._collection.count()
            print(f"Collection Count: {count}")
        except Exception as e:
            print(f"Collection Count Failed: {e}")
    return _vectorstore


def _get_retriever():
    """Lazy-load the ParentDocumentRetriever (cached after first call)."""
    global _retriever, _docstore

    if _retriever is None:
        print("===================================")
        print("Loading Parent Store & Retriever...")
        print("===================================")
        start = time.time()

        store = LocalFileStore(os.path.join(_PROJECT_ROOT, "parent_store"))
        _docstore = create_kv_docstore(store)

        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=300,
        )
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=80,
        )

        _retriever = ParentDocumentRetriever(
            vectorstore=_get_vectorstore(),
            docstore=_docstore,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
            search_kwargs={"k": 10},   # retrieve 10 child candidates, then fetch parents
        )
        print(f"Parent Retriever Ready in {time.time() - start:.2f}s")

    return _retriever


def _get_bm25_and_docs():
    """
    Lazy-load BM25 index.
    Fix 2: Load from disk cache if available, otherwise build and save.
    """
    global _bm25, _documents, _metadatas

    if _bm25 is not None:
        return _bm25, _documents, _metadatas

    # Try loading from disk cache first
    if os.path.exists(BM25_CACHE_PATH):
        print("===================================")
        print("Loading BM25 from cache...")
        print("===================================")
        start = time.time()
        with open(BM25_CACHE_PATH, "rb") as f:
            cache = pickle.load(f)
        _bm25 = cache["bm25"]
        _documents = cache["documents"]
        _metadatas = cache["metadatas"]
        print(f"BM25 Loaded from cache in {time.time() - start:.2f}s "
              f"({len(_documents)} chunks)")
    else:
        print("===================================")
        print("Building BM25 Index (first time only)...")
        print("===================================")

        start = time.time()
        all_docs = _get_vectorstore().get()
        _documents = all_docs["documents"]
        _metadatas = all_docs["metadatas"]
        print(f"Fetched {len(_documents)} child chunks from vectorstore "
              f"in {time.time() - start:.2f}s")

        if _documents:
            start = time.time()
            tokenized_docs = [doc.split() for doc in _documents]
            _bm25 = BM25Okapi(tokenized_docs)

            # Save to disk so next restart skips this step
            with open(BM25_CACHE_PATH, "wb") as f:
                pickle.dump({
                    "bm25": _bm25,
                    "documents": _documents,
                    "metadatas": _metadatas
                }, f)
            print(f"BM25 Built & cached in {time.time() - start:.2f}s")
        else:
            print("BM25 skipped — vectorstore is empty.")

    return _bm25, _documents, _metadatas


def _get_reranker():
    """
    Lazy-load CrossEncoder.
    Fix 3: Use a lightweight MiniLM reranker (~10x faster than bge-reranker-base on CPU).
    """
    global _reranker
    if _reranker is None:
        print("===================================")
        print("Loading Reranker (first time only)...")
        print("===================================")
        start = time.time()
        # Swap: MiniLM-L-2-v2 is ~10x faster than bge-reranker-base on CPU
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-2-v2")
        print(f"Reranker Loaded in {time.time() - start:.2f}s")
    return _reranker


def hybrid_search(query, top_k=5):
    """
    Hybrid search: vector + BM25 → deduplicate → rerank.
    All models are lazy-loaded on first call.
    """

    retriever = _get_retriever()
    bm25, documents, metadatas = _get_bm25_and_docs()
    reranker = _get_reranker()

    # ========================
    # VECTOR SEARCH
    # Use retriever.invoke() to get full PARENT chunks (2000 chars).
    # Falls back to direct child-chunk search if parent lookup returns nothing
    # (e.g. docstore key mismatch after re-ingestion).
    # ========================
    vector_results = retriever.invoke(query)
    print(f"[hybrid_search] ParentDocumentRetriever returned {len(vector_results)} docs")

    if not vector_results:
        print("[hybrid_search] WARNING: Parent retriever returned 0 docs. "
              "Falling back to direct vectorstore search (child chunks).")
        vector_results = _get_vectorstore().similarity_search(query, k=10)

    # ========================
    # BM25 SEARCH
    # Retrieve top 10 candidates for reranker
    # ========================
    tokenized_query = query.split()

    if bm25 is not None and documents:
        bm25_scores = bm25.get_scores(tokenized_query)
        bm25_top_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:10]

        bm25_results = [
            {"text": documents[idx], "metadata": metadatas[idx]}
            for idx in bm25_top_indices
        ]
    else:
        bm25_results = []

    # ========================
    # MERGE RESULTS
    # ========================
    combined = [
        {"text": doc.page_content, "metadata": doc.metadata}
        for doc in vector_results
    ]
    combined.extend(bm25_results)

    # ========================
    # REMOVE DUPLICATES
    # ========================
    seen = set()
    unique = []
    for item in combined:
        if item["text"] not in seen:
            seen.add(item["text"])
            unique.append(item)

    # ========================
    # RERANK
    # ========================
    pairs = [[query, item["text"]] for item in unique]
    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(unique, scores),
        key=lambda x: x[1],
        reverse=True
    )

    # ========================
    # SCORE THRESHOLD FILTER
    # The ms-marco-MiniLM reranker was trained on web queries and scores
    # technical/domain-specific documents much lower than -5.
    # Use -20.0 as a generous floor — only truly irrelevant chunks score below this.
    # ========================
    SCORE_THRESHOLD = -20.0
    ranked = [(chunk, score) for chunk, score in ranked if score >= SCORE_THRESHOLD]

    print(f"[hybrid_search] After threshold filter: {len(ranked)} docs remaining "
          f"(scores: {[round(float(s), 2) for _, s in ranked[:5]]}). "
          f"Returning top {min(top_k, len(ranked))}.")

    return ranked[:top_k]