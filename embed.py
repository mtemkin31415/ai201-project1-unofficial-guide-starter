"""
Milestone 4 (write side) — embed chunks into a local ChromaDB.

Reads chunks.jsonl (produced by ingest.py), embeds each chunk's text with
all-MiniLM-L6-v2, and stores the vectors + metadata in a persistent Chroma
collection on disk. Run this once after chunking; retrieve.py reads from it.

Usage:
    python embed.py                 # embed chunks.jsonl into ./chroma_db
    python embed.py --in chunks.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag_db import EMBED_MODEL, get_or_create_collection


def load_chunks(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found — run ingest.py first.")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed chunks into ChromaDB.")
    parser.add_argument("--in", dest="infile", default="chunks.jsonl", help="input JSONL of chunks")
    parser.add_argument("--batch", type=int, default=64, help="embedding batch size")
    args = parser.parse_args()

    chunks = load_chunks(Path(args.infile))
    print(f"Loaded {len(chunks)} chunks from {args.infile}")
    print(f"Embedding with {EMBED_MODEL} (first run downloads the model ~80MB)...")

    # reset=True keeps the script idempotent: re-running gives a clean rebuild
    # instead of duplicating or stacking chunks from a previous run.
    collection = get_or_create_collection(reset=True)

    # Chroma stores documents, metadata, and ids in parallel lists. We let the
    # collection's embedding function turn `documents` into vectors.
    for start in range(0, len(chunks), args.batch):
        batch = chunks[start:start + args.batch]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[
                {
                    "source": c["source"],
                    "source_file": c["source_file"],
                    "chunk_index": c["chunk_index"],
                    "token_count": c["token_count"],
                }
                for c in batch
            ],
        )
        print(f"  embedded {min(start + args.batch, len(chunks))}/{len(chunks)}")

    print(f"Done. Collection now holds {collection.count()} chunks at ./chroma_db")


if __name__ == "__main__":
    main()
