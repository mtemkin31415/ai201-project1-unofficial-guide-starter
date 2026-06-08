# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

---Domain: Binghamton University Campus Dining. This info may be hard to find because Binghamton University is undergoing a dining transition from one dining vendor to another. So students' may find it difficult to locate all the info regarding the new systems vs the old.

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 |  | Meal Plan FAQ | Website | https://dineoncampus.com/binghamton/meal-plan-faq
| 2 |  | Nutrition and Allergens | Website | https://dineoncampus.com/binghamton/nutrition--allergens
| 3 |  | Meet your Dietitians | Website | https://dineoncampus.com/binghamton/meet-your-dietitians
| 4 | | Campus Meal Plans | Website | https://dineoncampus.com/binghamton/campus-meal-plans-
| 5 | | Binghamton University Dining Transition| Website |  https://www.binghamton.edu/services/auxiliary/dining/dining-updates.html 
| 6 | | Dining Chanes Coming in 2026 | Website |  https://www.binghamton.edu/services/auxiliary/dining/dining-rfp.html
| 7 | | How bad is binghamton university's dining system, really? | Blog | https://weatherpatterns.bearblog.dev/bing-dining/
| 8 | | What is your favorite dining hall? | Thread | https://www.reddit.com/r/BinghamtonUniversity/comments/956bun/what_is_your_favorite_dining_hall/
| 9 | |  Dining Hauls: A Tour of Binghamton’s Delicious Dining Options | Blog  | https://www.binghamton.edu/news/blog/story/4480/dining-hauls-a-tour-of-binghamtons-delicious-dining-options
| 10 | |  Dining Services | Webpage |  https://www.binghamton.edu/services/auxiliary/dining/

---


## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 240 tokens.

**Overlap:** 40 tokens 

**Reasoning:**

--- I split recursively: paragraphs -> sentences -> words. Paragraphs that fit stay whole (so a FAQ header + its 2-3 sentence answer, or a bullet list, lands in one chunk); only oversized paragraphs fall back to sentence and then word splitting. The greedy packer recombines short units (bullets, Reddit comments) up to the size budget so they aren't stranded as context-poor fragments.

I originally planned 350 tokens, but lowered it to 240 once I saw the conflict with my embedding model: all-MiniLM-L6-v2 only embeds the first 256 tokens and silently truncates the rest. At 350 tokens, 45 of 51 chunks would have lost their tails at embed time. At 240/40, nearly all chunks fit the model's window (85 chunks total), so retrieval uses the full chunk text. The 40-token overlap (~17%) is insurance against a key sentence landing on a boundary — most important for the dense FAQ pages.

Preprocessing: stripped "(opens in a new window)" artifacts and normalized whitespace on every document; for the Reddit thread I additionally removed UI noise (vote counts, "8y ago" timestamps, avatar lines, the CommonMisspellingBot block, and the promoted Spotify post). Each chunk is prefixed with its source title (e.g. "[Meal Plan FAQ] ...") so short fragments stay retrievable and carry source attribution into generation. Implemented in ingest.py.

**Final chunk count:** 85 chunks across 10 documents.

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** ali-MiniLM-L6-v2 via Sentence Transformer

**Top-k:** 4 chunks

**Production tradeoff reflection:**

--- If I was impolementing this for real users I would consider:
Phrasing: Some people refer to dining hall differently than what is written on the official websites (Slang). Using a stronger transformer could probably detect relationships between what people say and what they mean
Latency & Cost: API models add network round trips and per token cost rather than a free local interface. Having a lot of people running queries simultaneously would increase latency greatly. Need to make interface and model scalable.
Multi-lingual support: Translating answers will lose some context for user that speak/more comfortable with a different language


## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
View the SYSTEM_PROMPT in generate.py 42-58 I structured the response like this. Give context as to what the AI is (Binghamton Dining AI), then 
give it some ground rules: chunks dropped if they don't reach the min score, ONLY use data retrieved from the prompts and give a fixed I don't know string if the answer isn't there.
**How source attribution is surfaced in the response:**
I stored each chunk with metadata from the doucments (Docuemnt Source Name & Chunk #). Then I put a rule in the AI prompt which tells the AI to retrieve and source all details it says. I also hardcoded a retrieval that is seprate from teh response that lists all the chunks used in the response that may or may not be cited by the AI.
---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | How many dining halls are there? | 6  | 4 | Gives accurate info from its understanding, but not all 6 dining halls were mentioned in a single chunk. Partially Relevant / Partially Accurate
| 2 |  What to do if I have allergies/diety restrictions? | Binghamton has food tags that go with common diet restrictions | A number of different ways to handl;e food aleergies | Respobnse is accurate and decently thourough giving multipl options | Relevant | Accurate
| 3 | When is the dining hall transition taking place? |  Summer 2026 | This summer | Acurate and gives an explanation why Partially Relevant | Accurate
| 4 | How can I pay for food in the dining halls and what food plans are there? | Pay with cash/ meal plan card. There are 8 meal plans. | Names all meal plans and gives a summary of each. Relevant | Accurate
| 5 | Where can I eat on campus this summer? | Most dining halls are closed limited availabillity | Gives two options with specific dates. Does not mention all dining halls are closed. | Partially Relevant | Partially Accurate

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
How many dining halls are there?

**What the system returned:**
It said that there are at least 4. When there are 6 dining halls + other restaurants

**Root cause (tied to a specific pipeline stage):**
Chunking - The chunks that returned the answers didn't contain all dining halls becuase in my sources they were spread out across multiple articles/paragraphs. Incorrect chunking practice Chunks too narrow

**What you would change to fix it:**
Widen the chunks used. I would need to use a different embedder as the one I used only allows for up to 256 chracters whihc is clearly to small for this question. I could also shrink the overlap as well.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
Writing the Chunking Strategy and Retrieval Approach sections before any code meant I had concrete numbers to hand directly to the AI tool, instead of vague instructions like "split the documents up." Because the spec named both my chunk size *and* my embedding model in the same document, the conflict between them surfaced immediately — a 240/40 chunk target read right next to "all-MiniLM-L6-v2" made it obvious to check the model's input limit before I embedded anything. The spec basically did the thinking up front so implementation was mostly translation.

**One way your implementation diverged from the spec, and why:**
My original plan was 350-token chunks with 60-token overlap. During implementation I learned that all-MiniLM-L6-v2 only embeds the first 256 tokens of any input and silently truncates the rest, so at 350 tokens roughly 45 of my chunks would have lost their tails before they were ever embedded. I dropped to 240 tokens with 40 overlap so nearly every chunk fits the model's window, which raised my total chunk count from 51 to 85. I then went back and updated the Chunking Strategy section of planning.md to match, since the spec is supposed to reflect the system I actually built.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1 — Ingestion and chunking**

- What I gave the AI:* My Chunking Strategy section from planning.md (350-token chunks, 60 overlap, recursive paragraph→sentence→word splitting) plus a description of my documents — a mix of headered FAQ pages, bullet lists, and one messy Reddit thread — and asked it to write a script that loads, cleans, and chunks them.
- What it produced:* `ingest.py`, with generic cleaning, Reddit-specific noise removal (vote counts, "8y ago" timestamps, avatar lines, the CommonMisspellingBot block, the promoted Spotify post), a recursive splitter, and a source-title prefix on each chunk. It counts tokens with the actual all-MiniLM tokenizer when installed and falls back to an approximation otherwise.
- What I changed or overrode:* When I ran it, the summary showed 45 of 51 chunks exceeded all-MiniLM's 256-token limit. I overrode my own spec and dropped the chunk size from 350 to 240 and overlap from 60 to 40 so chunks fit the embedding window, then had it regenerate `chunks.jsonl` (85 chunks) and update planning.md.

**Instance 2 — Generation and interface**

- What I gave the AI:* My grounding requirement, the output format I wanted (answer + source list), my Groq + Gradio stack, and the pipeline diagram. I explicitly asked it to make grounding enforced, not just suggested, and source attribution programmatic rather than left to the LLM.
- What it produced: `generate.py` ) and `app.py` (the Gradio interface), plus a review pointing out that inline `[n]` citations are still the LLM's even though the displayed source list is code-guaranteed.
- What I changed or overrrode: I gave it the specific interface skeleton my assignment suggested — an end-to-end `ask()` function in a `query.py` module returning sources as a list of strings, feeding plain `Textbox` outputs — and had it refactor `app.py` to match that structure instead of its original Markdown-based version, while keeping the programmatic source attribution intact.
