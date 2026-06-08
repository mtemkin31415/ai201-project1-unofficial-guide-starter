"""
Milestone 5 (interface) — Gradio front end for the Unofficial Bing Dining Guide.

Answer and sources are kept in SEPARATE outputs. The source list comes from
query.ask()'s programmatic list (built from retrieval metadata), so attribution
is guaranteed by code even if the LLM forgets to cite inline.

Run:
    python app.py        # serves at http://127.0.0.1:7860
"""

import gradio as gr

from query import ask


def handle_query(question):
    if not question or not question.strip():
        return "Ask a question about Binghamton University dining.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"]) or "(no matching sources — answer withheld)"
    return result["answer"], sources


with gr.Blocks(title="Unofficial Bing Dining Guide") as demo:
    gr.Markdown(
        "# 🍽️ The Unofficial Guide to Binghamton University Dining\n"
        "Answers are drawn **only** from the collected dining sources."
    )

    inp = gr.Textbox(label="Your question", placeholder="e.g. When do Dining Dollars expire?")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

    gr.Examples(
        examples=[
            "When is the dining hall transition taking place?",
            "How many dining halls are there?",
            "What should I do if I have a food allergy?",
            "Do Dining Dollars roll over between semesters?",
        ],
        inputs=inp,
    )


if __name__ == "__main__":
    demo.launch()
