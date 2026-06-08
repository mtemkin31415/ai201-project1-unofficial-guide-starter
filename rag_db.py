"""
Shared ChromaDB setup for the RAG pipeline.

Both embed.py (write side) and retrieve.py (read side) import from here so they
use the *same* model, collection name, and on-disk location. That guarantees the
query at retrieval time is embedded with the exact model the chunks were stored
with — if those ever drifted apart, similarity search would be meaningless.
"""

from __future__ import annotations

import chromadb
from chromadb.utils import embedding_functions

# Persisted to ./chroma_db (already in .gitignore). PersistentClient writes the
# index to disk, so you embed once and reuse it across runs.
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "bing_dining"
EMBED_MODEL = "all-MiniLM-L6-v2"   # matches planning.md Retrieval Approach


def get_embedding_function():
    """The all-MiniLM-L6-v2 embedder, run locally via sentence-transformers.

    Chroma calls this for us on both add() (documents) and query() (the user's
    question), so we never have to embed by hand.
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)


def get_client() -> "chromadb.api.ClientAPI":
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_or_create_collection(reset: bool = False):
    """Return the collection, optionally wiping it first.

    cosine space: all-MiniLM vectors are normalized, so cosine distance is the
    right similarity metric (and what the model was trained for).
    """
    client = get_client()
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # didn't exist yet — fine
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )
