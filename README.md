# DocuMind — AI Document Intelligence

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![LangChain](https://img.shields.io/badge/LangChain-1.3-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**Upload any PDF document and ask questions using advanced AI.**
Powered by hybrid semantic + keyword search with cross-encoder reranking.

[Live Demo](#) · [API Docs](http://localhost:8000/docs) · [Report Bug](#)

</div>

---

## ✨ Features

- 📎 **Upload any PDF** — drag-and-drop ingestion of any document domain
- 🔍 **Hybrid Search** — combines dense vector search (ChromaDB) with sparse BM25 keyword search
- 🎯 **Cross-Encoder Reranking** — MiniLM reranker re-scores candidates for precision
- 👪 **Parent-Child Chunking** — retrieves small child chunks for matching, returns full parent context for rich answers
- 💬 **Conversation Memory** — retains last 5 turns of context per session
- 📄 **Source Citations** — every answer includes the source filename and page number
- ⚡ **Fast Inference** — Groq-hosted Llama 3.1 8B for sub-2s LLM responses
- 🐳 **Docker Ready** — single-command deployment

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                  React Frontend (Vite)               │
│  Chat UI · PDF Upload · Source Citations · Sessions  │
└──────────────────┬───────────────────────────────────┘
                   │ HTTP (REST)
┌──────────────────▼───────────────────────────────────┐
│              FastAPI Backend                         │
│   /ask · /upload · /health · /debug/retrieval        │
└──────┬───────────────────┬────────────────────────────┘
       │                   │
┌──────▼──────┐   ┌────────▼────────────────────────────┐
│  Groq API   │   │      Hybrid Retrieval Pipeline       │
│ Llama 3.1   │   │                                      │
│  8B Instant │   │  ┌─────────────┐  ┌──────────────┐  │
└─────────────┘   │  │ Vector Store│  │  BM25 Index  │  │
                  │  │  (ChromaDB) │  │  (rank-bm25) │  │
                  │  └──────┬──────┘  └──────┬───────┘  │
                  │         └────────┬────────┘          │
                  │          ┌───────▼───────┐           │
                  │          │ CrossEncoder  │           │
                  │          │   Reranker    │           │
                  │          │(MiniLM-L-2-v2)│           │
                  │          └───────────────┘           │
                  └──────────────────────────────────────┘
```

**Embedding Model**: `BAAI/bge-base-en-v1.5` (local, 768-dim)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Groq API Key](https://console.groq.com) (free)

### 1. Clone & setup

```bash
git clone https://github.com/YOUR_USERNAME/documind.git
cd documind

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install Python deps
pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Ingest documents

```bash
# Ingest all PDFs from a directory
cd app
python -m ingestion.ingest /path/to/your/pdfs/
```

### 3. Run the backend

```bash
cd app
uvicorn main:app --reload --port 8000
# API docs available at http://localhost:8000/docs
```

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## 🐳 Docker

```bash
# Build and run with docker-compose
docker-compose up --build

# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | API status + vectorstore chunk count |
| `POST` | `/ask` | Ask a question (supports `session_id`) |
| `POST` | `/upload` | Upload PDFs for ingestion |
| `GET`  | `/debug/retrieval?q=...` | Inspect retrieved chunks for a query |

### Example: Ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main requirements?", "session_id": "my-session"}'
```

```json
{
  "answer": "The main requirements include...",
  "sources": [
    {"source": "/path/to/doc.pdf", "page": 3},
    {"source": "/path/to/doc.pdf", "page": 7}
  ]
}
```

### Example: Upload a PDF

```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@my_document.pdf"
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Groq Llama 3.1 8B Instant |
| **Embeddings** | BAAI/bge-base-en-v1.5 (local) |
| **Vector Store** | ChromaDB |
| **Keyword Search** | rank-bm25 |
| **Reranker** | cross-encoder/ms-marco-MiniLM-L-2-v2 |
| **Chunking** | Parent-Child (LangChain) |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | React 18 + Vite |
| **Containerization** | Docker + docker-compose |
| **Deployment** | Railway (backend) · Vercel (frontend) |

---

## 📁 Project Structure

```
documind/
├── app/
│   ├── main.py              # FastAPI entry point (CORS, middleware)
│   ├── config.py            # Settings via pydantic-settings
│   ├── logger.py            # Logging setup
│   ├── api/
│   │   ├── routes.py        # All API routes
│   │   └── upload.py        # PDF upload endpoint
│   ├── ingestion/
│   │   └── ingest.py        # Document ingestion pipeline
│   ├── retrieval/
│   │   └── hybrid_retriever.py  # Vector + BM25 + reranker
│   └── llm/
│       └── rag_chain.py     # LLM prompting + session memory
├── frontend/                # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── SourceCards.jsx
│   │   │   └── FileUpload.jsx
│   │   └── api/client.js
│   └── package.json
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📜 License

MIT — feel free to use this project in your portfolio or build on top of it.
