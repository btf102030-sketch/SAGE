#!/usr/bin/env python3
"""Query SAGE RAG with source/page citations."""

import os
from typing import List, Tuple

import chromadb
import ollama
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config import *


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)


def retrieve_context(collection, query, top_k=TOP_K_RESULTS):
    results = collection.query(query_texts=[query], n_results=top_k)
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    return chunks, metadatas


def format_citations(metadatas: List[dict]) -> List[str]:
    seen = set()
    citations = []
    for m in metadatas:
        src = os.path.basename(m.get("source", "unknown"))
        page = m.get("page")
        line = f"{src}" + (f" (p.{page})" if page is not None else "")
        if line not in seen:
            seen.add(line)
            citations.append(line)
    return citations


def build_prompt(context_chunks: List[str], metadatas: List[dict], query: str):
    tagged = []
    for chunk, meta in zip(context_chunks, metadatas):
        src = os.path.basename(meta.get("source", "unknown"))
        page = meta.get("page")
        label = f"[Source: {src}" + (f" | Page {page}]" if page is not None else "]")
        tagged.append(f"{label}\n{chunk}")

    context = "\n\n---\n\n".join(tagged)
    return f"""### CONTEXT FROM TECHNICAL DOCUMENTS:
{context}

### TECHNICIAN QUERY:
{query}

### DIAGNOSTIC RESPONSE:"""


def query_rag(user_query: str) -> Tuple[str, List[str]]:
    collection = get_collection()
    chunks, metadatas = retrieve_context(collection, user_query)

    prompt = build_prompt(chunks, metadatas, user_query)

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )

    answer = response["message"]["content"]
    citations = format_citations(metadatas)
    return answer, citations


if __name__ == "__main__":
    print("SAGE - System Analysis and Guidance Expert")
    print("Type 'exit' to quit.\n")
    while True:
        q = input("Technician Query: ").strip()
        if q.lower() == "exit":
            break
        if not q:
            continue

        ans, cites = query_rag(q)
        print("\n--- DIAGNOSTIC OUTPUT ---\n")
        print(ans)
        print("\n--- SOURCES ---")
        for c in cites:
            print(f"- {c}")
        print("\n--- END OF OUTPUT ---\n")
