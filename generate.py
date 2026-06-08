"""
Milestone 5 (generation) — grounded answer generation over retrieved chunks.

Grounding is enforced in THREE layers, so it does not depend on the LLM
behaving well:

1. Structural filter — chunks below MIN_SCORE are dropped before the model ever
   sees them; if nothing clears the bar, we return a fixed refusal and never
   call the LLM at all.
2. System prompt — the model is told to answer ONLY from the CONTEXT and to
   return a fixed refusal string when the context lacks the answer.
3. Programmatic source attribution — the source list is built in Python from
   the retrieved chunks' metadata and returned alongside the answer. It is NOT
   parsed from, or trusted to, the model output. Whatever the LLM writes, the
   sources shown to the user always reflect the chunks actually retrieved.

answer(query, k) is imported by app.py; this file is also runnable for testing:
    python generate.py "when do dining dollars expire?"
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

from retrieve import DEFAULT_TOP_K, retrieve

load_dotenv()

# Groq-hosted model. Swap for any current Groq chat model if this is retired
# (e.g. "llama-3.1-8b-instant" for a faster/cheaper option).
GROQ_MODEL = "llama-3.3-70b-versatile"

# Cosine-similarity floor. Chunks below this are treated as "not really about
# the question" and excluded — this is the structural half of grounding.
MIN_SCORE = 0.15

REFUSAL = "I don't have that information in the dining sources I was given."

SYSTEM_PROMPT = (
    "You are the Unofficial Guide to Binghamton University dining.\n"
    "Answer the user's question USING ONLY the numbered sources in the CONTEXT block.\n\n"
    "Rules:\n"
    "- Use only facts stated in the CONTEXT. Do NOT use outside knowledge, prior "
    "training, or assumptions.\n"
    f'- If the CONTEXT does not contain the answer, reply EXACTLY: "{REFUSAL}" '
    "and nothing else. Do not guess.\n"
    "- After each fact, cite the source number(s) it came from in square brackets, e.g. [1].\n"
    "- These sources include student opinions (e.g. Reddit); if sources disagree, "
    "say so and present both sides rather than picking one.\n"
    "- Be concise."
)


def _client() -> Groq:
    key = os.environ.get("GROQ_API_KEY")
    if not key or key == "your_key_here":
        raise SystemExit("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
    return Groq(api_key=key)


def _build_context(results: list[dict]) -> str:
    """Number each chunk so the model's [n] citations line up with the source list."""
    return "\n\n".join(
        f"[{i}] (source: {r['source']})\n{r['text']}" for i, r in enumerate(results, 1)
    )


def answer(query: str, k: int = DEFAULT_TOP_K) -> dict:
    """Return {'answer': str, 'sources': list[dict]} grounded in retrieved chunks."""
    results = retrieve(query, k)
    results = [r for r in results if r["score"] >= MIN_SCORE]  # structural grounding

    if not results:
        # Nothing relevant retrieved — refuse without calling the LLM.
        return {"answer": REFUSAL, "sources": []}

    user_msg = f"CONTEXT:\n{_build_context(results)}\n\nQUESTION: {query}"
    resp = _client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,  # low: we want faithful extraction, not creativity
    )
    answer_text = resp.choices[0].message.content.strip()

    # Programmatic source list, aligned 1:1 with the [n] numbering in the prompt.
    # Built from retrieval metadata, never from the model's text.
    sources = [
        {
            "n": i,
            "source": r["source"],
            "source_file": r["source_file"],
            "score": r["score"],
        }
        for i, r in enumerate(results, 1)
    ]
    return {"answer": answer_text, "sources": sources}


def _format_cli(result: dict) -> str:
    lines = [result["answer"], "", "Sources:"]
    if not result["sources"]:
        lines.append("  (none — answer withheld)")
    for s in result["sources"]:
        lines.append(f"  [{s['n']}] {s['source']} ({s['source_file']}, score {s['score']})")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or input("Question: ").strip()
    print(_format_cli(answer(q)))
