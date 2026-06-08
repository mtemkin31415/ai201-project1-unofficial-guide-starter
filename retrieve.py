"""
Milestone 4 (read side) — retrieval.

retrieve(query, k) embeds the user's question with the same model used at
embed time, runs a cosine similarity search over the Chroma collection, and
returns the top-k chunks with their source and a 0-1 similarity score.

Used as a library by the generation step (Milestone 5), and runnable directly
for testing:

    python retrieve.py "when do dining dollars expire?"
    python retrieve.py "best dining hall" --k 6
    python retrieve.py                       # interactive prompt loop
"""

from __future__ import annotations

import argparse

from rag_db import get_or_create_collection

DEFAULT_TOP_K = 4   # matches planning.md Retrieval Approach


def retrieve(query: str, k: int = DEFAULT_TOP_K) -> list[dict]:
    """Return the k most relevant chunks for `query`.

    Each result: {text, source, source_file, chunk_index, score}, ordered most
    relevant first. `score` is cosine similarity in [0, 1] (1 - distance), which
    is more intuitive than Chroma's raw distance.
    """
    collection = get_or_create_collection()
    if collection.count() == 0:
        raise SystemExit("Collection is empty — run embed.py first.")

    res = collection.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma nests results one level deep (one list per query); we sent one query.
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    results = []
    for doc, meta, dist in zip(docs, metas, dists):
        results.append(
            {
                "text": doc,
                "source": meta.get("source", "?"),
                "source_file": meta.get("source_file", "?"),
                "chunk_index": meta.get("chunk_index"),
                "score": round(1 - dist, 3),
            }
        )
    return results


def _print_results(query: str, results: list[dict]) -> None:
    print(f"\nQuery: {query}")
    print("=" * 70)
    for rank, r in enumerate(results, 1):
        print(f"[{rank}] score={r['score']}  source={r['source']} (chunk {r['chunk_index']})")
        snippet = r["text"] if len(r["text"]) <= 400 else r["text"][:400] + " ..."
        print(snippet)
        print("-" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve relevant chunks for a query.")
    parser.add_argument("query", nargs="*", help="the question (omit for interactive mode)")
    parser.add_argument("--k", type=int, default=DEFAULT_TOP_K, help="number of chunks to retrieve")
    args = parser.parse_args()

    if args.query:
        _print_results(" ".join(args.query), retrieve(" ".join(args.query), args.k))
        return

    print("Interactive retrieval. Blank line or Ctrl-C to quit.")
    try:
        while True:
            q = input("\n> ").strip()
            if not q:
                break
            _print_results(q, retrieve(q, args.k))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
