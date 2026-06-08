"""
Milestone 3 — Document ingestion and chunking.

Loads every .txt file in documents/, cleans it (with extra heuristics for the
noisy Reddit thread), and splits it into chunks that match the strategy in
planning.md:

    Chunk size: 240 tokens (kept under all-MiniLM-L6-v2's 256-token limit)
    Overlap:     40 tokens
    Method:      recursive — paragraphs -> sentences -> words

Token counting uses the *actual* all-MiniLM-L6-v2 tokenizer when
sentence-transformers / transformers are installed, so chunk sizes here line up
exactly with what gets embedded in Milestone 4. If those packages aren't
installed yet, it falls back to a ~4-chars-per-token approximation so the script
still runs.

Output: chunks.jsonl (one JSON object per line) plus a printed summary that
includes the total chunk count for the planning.md "Final chunk count" field.

Usage:
    python ingest.py                       # uses defaults from planning.md
    python ingest.py --chunk-size 350 --overlap 60
    python ingest.py --docs documents --out chunks.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# --------------------------------------------------------------------------- #
# Config — defaults mirror planning.md. Override on the command line if needed.
# --------------------------------------------------------------------------- #
DEFAULT_CHUNK_SIZE = 240          # tokens — kept under all-MiniLM's 256 limit
DEFAULT_OVERLAP = 40              # tokens (~17%)
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
PREPEND_SOURCE = True             # prefix each chunk with "[Source Title] " so
                                  # short, context-poor units (Reddit comments,
                                  # bullet points) stay retrievable and carry
                                  # attribution into Milestone 5.

# all-MiniLM-L6-v2 truncates input past 256 tokens at embed time. A 350-token
# chunk therefore loses its tail when embedded. We keep 350 to match the spec,
# but warn so the tradeoff is visible. (Lower the chunk size to <=256 if you'd
# rather not lose any tokens.)
MODEL_MAX_TOKENS = 256


# --------------------------------------------------------------------------- #
# Token counting
# --------------------------------------------------------------------------- #
_tokenizer = None
_USING_REAL_TOKENIZER = False


def _get_tokenizer():
    """Lazy-load the real model tokenizer; return None if unavailable."""
    global _tokenizer, _USING_REAL_TOKENIZER
    if _tokenizer is not None:
        return _tokenizer
    try:
        from transformers import AutoTokenizer  # type: ignore

        _tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
        _USING_REAL_TOKENIZER = True
    except Exception:
        _tokenizer = None
    return _tokenizer


def count_tokens(text: str) -> int:
    """Number of tokens in `text`.

    Uses the all-MiniLM-L6-v2 tokenizer when available (exact), otherwise a
    ~4-characters-per-token approximation. The chunker calls this everywhere, so
    both paths stay internally consistent.
    """
    tok = _get_tokenizer()
    if tok is not None:
        # add_special_tokens=False: we want raw content length, not +[CLS]/[SEP].
        return len(tok.encode(text, add_special_tokens=False))
    return max(1, round(len(text) / 4))


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
def clean_generic(text: str) -> str:
    """Cleaning applied to every document."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("(opens in a new window)", "")
    # strip trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # collapse 3+ blank lines down to a single paragraph break
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Lines from the Reddit export that are pure UI/metadata noise, not content.
_REDDIT_NOISE = [
    re.compile(r"^\d+$"),                              # standalone vote counts
    re.compile(r"^•$"),                                # bullet separators
    re.compile(r"^\d+\s*(y|mo|d|h|m)\s*ago$", re.I),   # "8y ago", "3 mo ago"
    re.compile(r"avatar$", re.I),                      # "u/srslybr0 avatar"
    re.compile(r"^OP$"),
    re.compile(r"^\[deleted\]$", re.I),
    re.compile(r"^Comment deleted by user$", re.I),
    re.compile(r"^Promoted$", re.I),
    re.compile(r"^\d+\s+more repl(y|ies)$", re.I),     # "3 more replies"
    re.compile(r"^u/spotify$", re.I),
    re.compile(r"^Prompt a playlist", re.I),           # promoted Spotify block
    re.compile(r"^Learn More$", re.I),
    re.compile(r"^spotify\.app\.link$", re.I),
    re.compile(r"^Clickable image", re.I),
    re.compile(r"^Collapse video player$", re.I),
    re.compile(r"^\d+:\d+\s*/\s*\d+:\d+$"),            # "0:00 / 0:00"
    re.compile(r"CommonMisspellingBot", re.I),
    re.compile(r"^Hey, .*just a quick heads-up:$", re.I),
    re.compile(r"alot is actually spelled", re.I),
    re.compile(r"^The parent commenter can reply", re.I),
    re.compile(r"^\[For official purposes only\]$", re.I),
]


def clean_reddit(text: str) -> str:
    """Generic cleaning + drop the thread's UI chrome and bot noise.

    This is a best-effort heuristic for *this* export; standalone usernames that
    look like ordinary words are intentionally left in (detecting them reliably
    isn't worth the false positives on real content).
    """
    text = clean_generic(text)
    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and any(p.search(stripped) for p in _REDDIT_NOISE):
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_document(text: str, filename: str) -> str:
    if "reddit" in filename.lower():
        return clean_reddit(text)
    return clean_generic(text)


# --------------------------------------------------------------------------- #
# Recursive splitting: paragraphs -> sentences -> words
# --------------------------------------------------------------------------- #
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _split_words(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Last resort: window a too-long sentence by words, with token overlap."""
    words = text.split()
    windows: list[str] = []
    start = 0
    while start < len(words):
        end = start
        piece: list[str] = []
        while end < len(words) and count_tokens(" ".join(piece + [words[end]])) <= chunk_size:
            piece.append(words[end])
            end += 1
        if not piece:  # single word longer than chunk_size — emit it alone
            piece = [words[start]]
            end = start + 1
        windows.append(" ".join(piece))
        if end >= len(words):
            break
        # step back so the next window overlaps by ~`overlap` tokens
        back = 0
        while back < len(piece) and count_tokens(" ".join(piece[len(piece) - back - 1:])) <= overlap:
            back += 1
        start = end - back if back else end
    return windows


def _atomic_segments(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Break a document into units that are each <= chunk_size tokens.

    Paragraphs that fit stay whole; oversized paragraphs split into sentences;
    oversized sentences split into word windows. The packer then recombines
    these units up to the chunk budget.
    """
    segments: list[str] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for para in paragraphs:
        if count_tokens(para) <= chunk_size:
            segments.append(para)
            continue
        for sentence in _SENTENCE_BOUNDARY.split(para):
            sentence = sentence.strip()
            if not sentence:
                continue
            if count_tokens(sentence) <= chunk_size:
                segments.append(sentence)
            else:
                segments.extend(_split_words(sentence, chunk_size, overlap))
    return segments


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Pack atomic segments greedily into <=chunk_size chunks with token overlap.

    Overlap is seeded from the tail segments of the previous chunk, so it always
    breaks on a clean paragraph/sentence boundary rather than mid-word.
    """
    segments = [(s, count_tokens(s)) for s in _atomic_segments(text, chunk_size, overlap)]

    chunks: list[str] = []
    current: list[tuple[str, int]] = []
    current_tokens = 0

    for seg, tok in segments:
        if current and current_tokens + tok > chunk_size:
            chunks.append("\n".join(s for s, _ in current))
            # build overlap seed from the tail of the chunk we just closed
            seed: list[tuple[str, int]] = []
            seed_tokens = 0
            for s, t in reversed(current):
                if seed and seed_tokens + t > overlap:
                    break
                seed.insert(0, (s, t))
                seed_tokens += t
            current = list(seed)
            current_tokens = seed_tokens
        current.append((seg, tok))
        current_tokens += tok

    if current:
        chunks.append("\n".join(s for s, _ in current))
    return chunks


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def title_from_filename(path: Path) -> str:
    """'Meal_Plan_FAQ.txt' -> 'Meal Plan FAQ'."""
    return path.stem.replace("_", " ").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest and chunk documents for the RAG pipeline.")
    parser.add_argument("--docs", default="documents", help="folder of .txt source documents")
    parser.add_argument("--out", default="chunks.jsonl", help="output JSONL path")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="max tokens per chunk")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="token overlap between chunks")
    args = parser.parse_args()

    docs_dir = Path(args.docs)
    files = sorted(docs_dir.glob("*.txt"))
    if not files:
        raise SystemExit(f"No .txt files found in {docs_dir.resolve()}")

    # Trigger tokenizer load so the summary can report which mode we're in.
    count_tokens("warmup")
    mode = "all-MiniLM-L6-v2 tokenizer (exact)" if _USING_REAL_TOKENIZER else "~4 chars/token approximation"
    print(f"Token counting:  {mode}")
    print(f"Chunk size:      {args.chunk_size} tokens   |   Overlap: {args.overlap} tokens")
    if args.chunk_size > MODEL_MAX_TOKENS:
        print(
            f"  ! note: chunks over {MODEL_MAX_TOKENS} tokens are truncated by all-MiniLM-L6-v2 "
            f"at embed time."
        )
    print("-" * 70)

    records = []
    per_file_counts: dict[str, int] = {}
    oversized_truncating = 0

    for path in files:
        raw = path.read_text(encoding="utf-8")
        source = title_from_filename(path)
        cleaned = clean_document(raw, path.name)
        chunks = chunk_text(cleaned, args.chunk_size, args.overlap)
        per_file_counts[path.name] = len(chunks)

        for i, body in enumerate(chunks):
            text = f"[{source}] {body}" if PREPEND_SOURCE else body
            tokens = count_tokens(text)
            if tokens > MODEL_MAX_TOKENS:
                oversized_truncating += 1
            records.append(
                {
                    "id": f"{path.stem}-{i}",
                    "source": source,
                    "source_file": path.name,
                    "chunk_index": i,
                    "token_count": tokens,
                    "text": text,
                }
            )

    out_path = Path(args.out)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ----- summary -----
    for name, n in per_file_counts.items():
        print(f"  {name:<28} {n:>3} chunks")
    print("-" * 70)
    total = len(records)
    avg = sum(r["token_count"] for r in records) / total if total else 0
    print(f"Documents:       {len(files)}")
    print(f"Total chunks:    {total}    (use this for planning.md 'Final chunk count')")
    print(f"Avg tokens/chunk: {avg:.0f}")
    if oversized_truncating:
        print(f"Chunks > {MODEL_MAX_TOKENS} tokens (will truncate at embed): {oversized_truncating}")
    print(f"Wrote:           {out_path.resolve()}")
    

if __name__ == "__main__":
    main()
