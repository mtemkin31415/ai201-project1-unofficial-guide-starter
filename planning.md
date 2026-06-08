# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

---Domain: Binghamton University Campus Dining. This info may be hard to find because Binghamton University is undergoing a dining transition from one dining vendor to another. So students' may find it difficult to locate all the info regarding the new systems vs the old.

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

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

**Overlap:** 40 tokens (~17%).

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


## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | How many dining halls are there? | 6
| 2 | What to do if I have allergies/diety restrictions? | Binghamton has food tags that go with common diet restrictions
| 3 | When is the dining hall transition taking place? |  Fall 2027
| 4 | How can I pay for food in the dining halls and what food plans are there? | Pay with cash/ meal plan card. There are 8 meal plans.
| 5 | Wherte to eat on campus this summer?

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.  Chunking - There are bonund to be chunking errors no matter how finely I tune the ingestion algorithm. I believe a chunking algorithm based on context would make the most sense when we are ingesting multiple file sources. No one size fits all solution

2. Some info may be missing from the required resources or contradictory. Think of the reddit rankings I included where dining halls are ranked differently by person

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```
 documents/*.txt
       │
       ▼
┌──────────────────┐   clean (generic + Reddit noise removal),
│ 1. Ingestion +   │   recursive split: paragraphs→sentences→words,
│    Chunking      │   240-tok chunks / 40 overlap, prefix [Source]
│   ingest.py      │
└──────────────────┘
       │  chunks.jsonl  (85 chunks + metadata)
       ▼
┌──────────────────┐   all-MiniLM-L6-v2 (sentence-transformers)
│ 2. Embedding +   │   embed each chunk → vector
│    Vector Store  │   store in persistent ChromaDB (cosine)
│ embed.py/rag_db  │
└──────────────────┘
       │  ./chroma_db
       ▼
┌──────────────────┐   embed user query with SAME model,
│ 3. Retrieval     │   cosine top-k=4, return text + source + score
│   retrieve.py    │
└──────────────────┘
       │  top-4 chunks
       ▼
┌──────────────────┐   Groq (llama-3.3-70b) with a grounding system
│ 4. Generation    │   prompt; source list built in Python from the
│   generate.py    │   retrieved chunks (not from the LLM)
└──────────────────┘
       │  answer + sources
       ▼
┌──────────────────┐
│ 5. Interface     │   Gradio: question box → answer + source panel
│    app.py        │
└──────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
Total: 86 random chunks across 10 pages
5 random chunks:
{"id": "Campus_Meal_Plans-0", "source": "Campus Meal Plans", "source_file": "Campus_Meal_Plans.txt", "chunk_index": 0, "token_count": 198, "text": "[Campus Meal Plans] Campus Meal Plans\nWhen you live on campus, you have the added convenience of dining facilities being steps away from your front door. All students living on campus are required to have a meal plan.\nFor any questions regarding meal plans, please email eatatbing@compass-usa.com\nChoose Your Plan  |  Cost  | Dining Dollars\nPlan A              3665    3665\nPlan B              3520    3520\nPlan C              3375    3375\nPlan D              3250    3250\nPlan E              3160    3160\nPlan F              2935    2935\nCommuter semester   415     415\nConvenience Plan    30      30\nWILL I BE CHARGED AN ADMINISTRATIVE FEE ON MY MEAL PLAN FOR FALL 2026-27?\nBearcat Dining meal plans will not have an administrative fee charged to student accounts for this coming school year."}
{"id": "Meet_Your_Dietitians-4", "source": "Meet Your Dietitians", "source_file": "Meet_Your_Dietitians.txt", "chunk_index": 4, "token_count": 56, "text": "[Meet Your Dietitians] Available dining options for religious diets, such as Halal and Kosher\nAvailable plant-forward dining options\nSports nutrition\nDigestive disorders\nDisordered eating\nSchedule for Alexa\nSchedule for Julia"}
{"id": "Binghamton_Food_Blog-4", "source": "Binghamton Food Blog", "source_file": "Binghamton_Food_Blog.txt", "chunk_index": 4, "token_count": 198, "text": "[Binghamton Food Blog] [The following numbers are all rounded for clarity.]\nThe result of such a system is that each individual cost you pay in dining dollars is approximately 3x the money. For example, a $6 pasta bowl from C4 is de facto $18 out of pocket. In other words, you pay $2,000 for the privilege of paying $6 for that pasta. The true cost of food is masked behind a massive fee that many students may not even be fully aware of.\nHere’s where it gets weirder: anything with a brand name in the dining halls is charged at retail price on the dining dollars, so the Chobani yogurt at $2.50 (when it’s about $1.25 each at a grocery store) essentially means you are paying $7.50 for the yogurt. Just to dig in the point: you paid $2000 for the privilege to pay $2.50 for 5oz of yogurt."}
{"id": "Nutrition_Allergens-4", "source": "Nutrition Allergens", "source_file": "Nutrition_Allergens.txt", "chunk_index": 4, "token_count": 168, "text": "[Nutrition Allergens] Food Allergies and Special Diets\nBearcat Dining is here to support our students by ensuring a safe and delicious dining experience, especially if you have food allergies or medical conditions that require specific dietary restrictions. Our Registered Dietitians are available to meet and discuss dining options, accommodations, resources on campus, and more. Please contact our dietitians to best determine how Bearcat Dining can help meet your dietary and nutritional needs.\nPlease contact our Registered Dietitians: Alexa at alexa.schmidt@compass-usa.com or Julie at julielee@binghamton.edu to set up a meeting or dining hall tour.\nDelicious Without"}
{"id": "Dining_Transition-11", "source": "Dining Transition", "source_file": "Dining_Transition.txt", "chunk_index": 11, "token_count": 246, "text": "[Dining Transition] Expanded Halal and Kosher Access — Based on direct student feedback, Halal and Kosher options will be easier to discover and access across campus, including a new all-kosher truck, Nosh & Go, and a Kosher Grab n’ Go program that delivers every day convenience.\n\"Delicious Without\" Across Campus — Chartwells’ “Delicious Without” program, free from the top nine allergens and gluten, will expand to all four dining halls (C4, CIW, Hinman, and Appalachian), increasing safe and welcoming options for students with food allergies and sensitivities.\nTwo registered dietitians will be available to support students with special dietary needs and preferences.\nInternational-Inspired Food Hall at C4 — The C4 dining hall will debut a globally inspired food hall featuring Chartwells concepts such as Masala Dabba, an Indian inspired station, and La Mesa, a Latin concept.\nA dedicated kosher station will continue to serve as a cornerstone of inclusive dining on campus."}
I think generally these chunks make sense as they are self contained ideas that only talk about one specific subnject and are not overly long or short
**Milestone 4 — Embedding and retrieval:**
Query: How many dining halls are there?
======================================================================
[1] score=0.562  source=Dining Transition (chunk 22)
[Dining Transition] Planning is underway for updates to residential dining halls (Hinman, Appalachian, CIW, and C4) as well as all locations at the Marketplace.
New catering menu development is underway, and the catering website will be launched in May.  For events scheduled after May 18, requests can be submitted via email at Crafted1946@compass-usa.com

Query: What to do if I have allergies/dietary restriuctions?
======================================================================
[1] score=0.503  source=Nutrition Allergens (chunk 5)
[Nutrition Allergens] Delicious Without
Delicious Without supports an inclusive dining experience for those with food allergies and needing to avoid gluten. This dedicated space features food that is simply prepared, seasoned, and served by a trained associate. The station is dedicated to foods prepared without the nine major food allergens (milk, egg, wheat, soy, peanuts, tree nuts, fish, shellfi ...

Query: When is the dining hall transition taking place?
======================================================================
[1] score=0.615  source=Dining Transition (chunk 15)
[Dining Transition] May 1, 2026
Fall 2026 meal plan rates
Meal plan rates for the Fall 2026 semester are now available.
MarketPlace to close for the summer
To enhance your dining experience and reimagine our concepts and spaces, the MarketPlace in The Union will close for the summer beginning May 18.
We look forward to welcoming you back when we reopen in the fall. Information about summer dining  ...
----------------------------------------------------------------------
[2] score=0.614  source=Dining Transition (chunk 22)
[Dining Transition] Planning is underway for updates to residential dining halls (Hinman, Appalachian, CIW, and C4) as well as all locations at the Marketplace.
New catering menu development is underway, and the catering website will be launched in May.  For events scheduled after May 18, requests can be submitted via email at Crafted1946@compass-usa.com
For dining related questions, please contac ...
----------------------------------------------------------------------
[3] score=0.551  source=Dining Changes (chunk 2)
[Dining Changes] Will my meal plan change right away?
No. Current meal plan structures will remain the same through the first year of the new contract to allow time for planning and a smooth rollout of any future updates.
What happens to Dining Dollar balances during the transition from Sodexo to Chartwells Higher Education?
As the University transitions from Sodexo to Chartwells Higher Education  ...
----------------------------------------------------------------------
[4] score=0.55  source=Dining Transition (chunk 2)
[Dining Transition] As the Bearcat Dining Meal Plan office transitions, announcements and FAQs about purchasing meal plans for the fall can be found, here.
May 12, 2026
Summer dining options
As the University transitions to a new food service provider over the summer and some concepts are temporarily closed for renovations, alternative dining options will be made available temporarily. As previous ...

I think these chunks are relevant to the related queries and a return result of 4 chunks makes sense


**Milestone 5 — Generation and interface:**
