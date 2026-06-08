"""
End-to-end query function: question in, grounded answer + source list out.

This is the single entry point the interface (app.py) calls. It wraps
generate.answer() — which does retrieve -> ground -> generate — and reshapes the
programmatic source metadata into display strings.

Source attribution stays code-guaranteed: the strings here are built from the
retrieved chunks' metadata, NOT from anything the LLM wrote.

    from query import ask
    result = ask("when do dining dollars expire?")
    # -> {"answer": "...", "sources": ["[1] Meal Plan FAQ (Meal_Plan_FAQ.txt, relevance 0.61)", ...]}
"""

from __future__ import annotations

from generate import answer


def ask(question: str) -> dict:
    """Return {"answer": str, "sources": list[str]} for a user question."""
    result = answer(question)
    sources = [
        f"[{s['n']}] {s['source']} ({s['source_file']}, relevance {s['score']})"
        for s in result["sources"]
    ]
    return {"answer": result["answer"], "sources": sources}


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or input("Question: ").strip()
    out = ask(q)
    print(out["answer"])
    print("\nRetrieved from:")
    for s in out["sources"] or ["(none — answer withheld)"]:
        print(f"  • {s}")
