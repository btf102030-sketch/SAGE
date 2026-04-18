#!/usr/bin/env python3
"""
SAGE.ai Phase 1 MVP — FastAPI Backend
======================================
Provides REST endpoints for the SAGE desktop application.
Integrates with the existing SAGE RAG pipeline (query.py / ingest.py).

Endpoints:
    POST /query   — Accept a question, return an answer with citations
    POST /ingest  — Trigger document re-indexing
    GET  /status  — Health-check / system status

Deployment path on MLRS machine:  ~/sage/
This file should be placed alongside config.py, ingest.py, and query.py.

Run:
    uvicorn sage_api:app --host 0.0.0.0 --port 5000 --reload
"""

import os
import sys
import json
import time
import logging
import traceback
import subprocess
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sage_api.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("sage_api")

# ---------------------------------------------------------------------------
# Import SAGE core modules (config, query, ingest)
# They live in the same directory (~/sage/) at deployment time.
# ---------------------------------------------------------------------------
try:
    from config import (
        CHROMA_DIR,
        COLLECTION_NAME,
        EMBEDDING_MODEL,
        OLLAMA_MODEL,
        SYSTEM_PROMPT,
        TOP_K_RESULTS,
        DOCS_DIR,
    )
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    import ollama as ollama_client

    SAGE_CORE_AVAILABLE = True
    logger.info("SAGE core modules loaded successfully.")
except ImportError as exc:
    SAGE_CORE_AVAILABLE = False
    logger.warning("SAGE core modules NOT available (%s). Running in demo mode.", exc)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SAGE.ai API",
    version="1.0.0",
    description="REST API for SAGE — System Analysis & Guidance Engine",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory log buffer (for the Terminal page in the desktop app)
# ---------------------------------------------------------------------------
MAX_LOG_ENTRIES = 500
api_logs: list[dict] = []

def _log_event(level: str, message: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
    }
    api_logs.append(entry)
    if len(api_logs) > MAX_LOG_ENTRIES:
        api_logs.pop(0)
    getattr(logger, level.lower(), logger.info)(message)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None

class QueryResponse(BaseModel):
    answer: str
    citations: list[str]
    elapsed_seconds: float

class IngestResponse(BaseModel):
    status: str
    message: str
    elapsed_seconds: float

class StatusResponse(BaseModel):
    status: str
    sage_core: bool
    ollama_model: str
    chroma_dir: str
    docs_dir: str
    collection: str
    uptime_seconds: float
    log_entries: int

# ---------------------------------------------------------------------------
# Startup timestamp
# ---------------------------------------------------------------------------
_start_time = time.time()

# ---------------------------------------------------------------------------
# Helper: RAG query (wraps existing query.py logic)
# ---------------------------------------------------------------------------
def _rag_query(question: str, top_k: int) -> tuple[str, list[str]]:
    """Execute the full RAG pipeline and return (answer, citations)."""
    if not SAGE_CORE_AVAILABLE:
        return (
            "SAGE core is not available. Please ensure config.py, ingest.py, "
            "query.py, and all dependencies are installed in ~/sage/.",
            ["DEMO MODE — no live citations"],
        )

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)

    results = collection.query(query_texts=[question], n_results=top_k)
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]

    # Build citations
    seen = set()
    citations: list[str] = []
    for meta in metadatas:
        src = meta.get("source", "Unknown")
        page = meta.get("page", None)
        label = f"{src}" + (f" (p.{page})" if page else "")
        if label not in seen:
            seen.add(label)
            citations.append(label)

    # Build prompt
    context = "\n\n---\n\n".join(chunks)
    prompt = (
        f"### CONTEXT FROM TECHNICAL DOCUMENTS:\n{context}\n\n"
        f"### TECHNICIAN QUERY:\n{question}\n\n"
        f"### DIAGNOSTIC RESPONSE:"
    )

    # Call Ollama (non-streaming for API)
    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    answer = response["message"]["content"]
    return answer, citations

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    """Accept a technician question and return an AI-generated answer with citations."""
    _log_event("INFO", f"Query received: {req.question[:120]}…")
    t0 = time.time()
    try:
        top_k = req.top_k or (TOP_K_RESULTS if SAGE_CORE_AVAILABLE else 5)
        answer, citations = _rag_query(req.question, top_k)
        elapsed = round(time.time() - t0, 2)
        _log_event("INFO", f"Query answered in {elapsed}s — {len(citations)} citation(s)")
        return QueryResponse(answer=answer, citations=citations, elapsed_seconds=elapsed)
    except Exception as exc:
        elapsed = round(time.time() - t0, 2)
        tb = traceback.format_exc()
        _log_event("ERROR", f"Query failed: {exc}\n{tb}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint():
    """Trigger a full document re-index by running ingest.py."""
    _log_event("INFO", "Ingest triggered via API")
    t0 = time.time()
    try:
        # Run ingest.py as a subprocess so it can use its own imports cleanly
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ingest_script = os.path.join(base_dir, "ingest.py")
        if not os.path.isfile(ingest_script):
            raise FileNotFoundError(f"ingest.py not found at {ingest_script}")

        # Use the sage_venv python explicitly (fallback to current interpreter if missing).
        venv_python = os.path.realpath(os.path.join(base_dir, "../sage_venv/bin/python3"))
        python_exec = venv_python if os.path.isfile(venv_python) else sys.executable

        result = subprocess.run(
            [python_exec, ingest_script],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour for large document sets
        )
        elapsed = round(time.time() - t0, 2)
        if result.returncode != 0:
            _log_event("ERROR", f"Ingest failed (exit {result.returncode}): {result.stderr[:500]}")
            return IngestResponse(
                status="error",
                message=f"Ingest exited with code {result.returncode}. {result.stderr[:300]}",
                elapsed_seconds=elapsed,
            )
        _log_event("INFO", f"Ingest completed in {elapsed}s")
        return IngestResponse(status="ok", message="Re-indexing complete.", elapsed_seconds=elapsed)
    except Exception as exc:
        elapsed = round(time.time() - t0, 2)
        _log_event("ERROR", f"Ingest error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/status", response_model=StatusResponse)
async def status_endpoint():
    """Health-check and system status."""
    _log_event("INFO", "Status check")
    return StatusResponse(
        status="ok",
        sage_core=SAGE_CORE_AVAILABLE,
        ollama_model=OLLAMA_MODEL if SAGE_CORE_AVAILABLE else "N/A",
        chroma_dir=CHROMA_DIR if SAGE_CORE_AVAILABLE else "N/A",
        docs_dir=DOCS_DIR if SAGE_CORE_AVAILABLE else "N/A",
        collection=COLLECTION_NAME if SAGE_CORE_AVAILABLE else "N/A",
        uptime_seconds=round(time.time() - _start_time, 1),
        log_entries=len(api_logs),
    )


@app.get("/logs")
async def logs_endpoint(limit: int = 100):
    """Return recent API log entries (for the desktop Terminal page)."""
    return {"logs": api_logs[-limit:]}


# ---------------------------------------------------------------------------
# Run with uvicorn when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting SAGE.ai API on port 5000…")
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
