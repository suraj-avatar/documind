from dotenv import load_dotenv
load_dotenv()

import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from retrieval.hybrid_retriever import hybrid_search

# ------------------------
# LLM — temperature=0.1 for factual, document-grounded answers
# (0.5 was too high and caused hallucinations)
# ------------------------

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.1
)

# ------------------------
# SESSION HISTORY STORE
# Keyed by session_id → list of {"role": "user"/"assistant", "content": str}
# Keeps the last MAX_HISTORY turns for context retention.
# ------------------------

_session_store: dict[str, list[dict]] = {}
MAX_HISTORY = 5   # number of past Q&A turns to include


def _get_history(session_id: str) -> list[dict]:
    return _session_store.get(session_id, [])


def _save_turn(session_id: str, question: str, answer: str):
    if session_id not in _session_store:
        _session_store[session_id] = []
    _session_store[session_id].append({"role": "user",      "content": question})
    _session_store[session_id].append({"role": "assistant", "content": answer})
    # Keep only the last MAX_HISTORY turns (each turn = 2 messages)
    _session_store[session_id] = _session_store[session_id][-(MAX_HISTORY * 2):]


def _format_history(history: list[dict]) -> str:
    if not history:
        return ""
    lines = ["--- Conversation History ---"]
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    lines.append("--- End of History ---")
    return "\n".join(lines)


def _format_context(retrieved_docs: list) -> str:
    """
    Build a labelled context string so the LLM knows which document
    each chunk comes from. Format:
        [Source: filename.pdf | Page: 3]
        <chunk text>
    """
    parts = []
    for chunk, score in retrieved_docs:
        source = chunk["metadata"].get("source", "unknown")
        page   = chunk["metadata"].get("page", "?")
        # Use just the filename, not the full path
        filename = os.path.basename(source)
        header = f"[Source: {filename} | Page: {page}]"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n".join(parts)


def generate_answer(query: str, session_id: str = "default") -> dict:

    # ------------------------
    # HYBRID RETRIEVAL
    # ------------------------
    retrieved_docs = hybrid_search(query)

    # ------------------------
    # BUILD LABELLED CONTEXT
    # ------------------------
    context = _format_context(retrieved_docs)

    # ------------------------
    # BUILD CONVERSATION HISTORY
    # ------------------------
    history = _get_history(session_id)
    history_text = _format_history(history)

    # ------------------------
    # PROMPT — SystemMessage + HumanMessage structure
    # ------------------------
    system_prompt = (
        "You are a helpful AI assistant that answers questions strictly based on "
        "the provided document context. "
        "Rules:\n"
        "- Answer ONLY from the context provided below.\n"
        "- Do NOT hallucinate or use outside knowledge.\n"
        "- If the answer is not found in the context, say exactly: "
        "\"Not available in the provided documents\".\n"
        "- Cite the source file and page number when relevant.\n"
        "- Be concise, accurate, and professional."
    )

    human_content = ""

    if history_text:
        human_content += f"{history_text}\n\n"

    human_content += (
        f"Document Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer:"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    # ------------------------
    # LLM CALL
    # ------------------------
    response = llm.invoke(messages)

    # Strip leading/trailing whitespace and collapse multiple blank lines
    import re
    answer = re.sub(r'\n{2,}', '\n', response.content).strip()

    # ------------------------
    # SAVE TURN TO HISTORY
    # ------------------------
    _save_turn(session_id, query, answer)

    return {
        "answer": answer,
        "sources": [
            chunk["metadata"]
            for chunk, _ in retrieved_docs
        ]
    }