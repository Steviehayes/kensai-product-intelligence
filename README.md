# Kensai — Product Intelligence Agent

A small full-stack agent that turns eight messy, conflicting supplement documents
into clean, **source-traceable** intelligence. It ingests the corpus into a
knowledge base, extracts structured product data, cross-checks every marketing
claim against the EU/UK health-claims reference, reconciles conflicts and gaps
across sources, and answers questions — with an exact source snippet behind every
answer and every table cell, and an honest "not found" where the corpus is silent.

> Built for the Kensai take-home. The documents (not the live web) are the source
> of truth.

---

## Live demo

**https://kensai-product-intelligence-441530711599.europe-west2.run.app**

Login (HTTP Basic Auth): username **`kensai`** · password **`Kensai-Review-2026`**

Hosted on Google Cloud Run (europe-west2, London): always-on HTTPS, scales to zero.
The public instance is behind a login so the endpoint can't be abused. It currently
runs in **deterministic mode** (TF-IDF retrieval + the fully-cited structured layer),
so the intelligence table, the flags report and the six answers all work. Setting a
`GOOGLE_API_KEY` (below) additionally enables the Gemini-backed natural-language chat
for open-ended questions.

---

## Run it (one command)

**Docker (recommended):**

```bash
git clone <this-repo> && cd kensai-product-intelligence
docker compose up --build
# open http://localhost:8000
```

It runs with **zero configuration**. Without an API key the agent uses TF-IDF
retrieval and a deterministic, fully-cited answer layer — the intelligence table,
the flags report and the six answers all work offline.

**To enable the full natural-language chat** (Google Gemini, free tier — covers
both embeddings and chat), add a key:

```bash
cp .env.example .env
# put a free key from https://aistudio.google.com/apikey into GOOGLE_API_KEY
docker compose up --build
```

**Local (without Docker):**

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # open http://localhost:8000
pytest -q                                    # run the checks
```

**Optional login.** Set both `APP_USER` and `APP_PASSWORD` to gate the whole app
(API + frontend) behind HTTP Basic Auth — that is how the hosted demo is protected.
Leave them unset and the app is open (the local default).

---

## Framework choice, and why

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | **FastAPI** | Tiny, typed, async; the briefing suggested it and it keeps the API surface (ingest / query / structured data) legible. |
| Agent | **Hand-rolled tool pipeline** (no LangChain/LlamaIndex) | The whole point is legible orchestration. A framework would hide the four steps behind abstractions; here each tool is ~80 lines you can read. |
| Embeddings / chat | **Google Gemini free tier** (`text-embedding-004`, `gemini-2.0-flash`) | Genuinely free for a public demo, covers embeddings *and* generation, no card required. Pluggable via one env var. |
| Retrieval store | **In-memory NumPy cosine** | The corpus is 8 docs (~15 chunks). A vector DB would be theatre; NumPy is honest and dependency-light. The `add`/`search` interface is what you'd keep when swapping in FAISS/pgvector. |
| Fallback | **scikit-learn TF-IDF** | So the app boots and answers with no key — a reviewer runs one command and sees real output. |
| Frontend | **One vanilla HTML file** | No build step, no `node_modules`; the same container serves API + UI. |

**Design principle that matters most here:** the extraction, compliance and
conflict layers are **deterministic**, not LLM-driven. On regulatory and nutrient
data you do not want a model to silently turn a µg into a mg or invent a value —
so every figure is parsed with unit-aware rules and pinned to the exact source
line. The LLM is used only to *phrase* an answer from evidence it is handed, never
as a source of facts. Determinism where correctness is non-negotiable; the LLM for
open-ended phrasing.

---

## The agent's steps and tools

Ingest (once, on startup) → then every question runs the chat loop.

```
INGEST PIPELINE
  load + chunk (8 docs, format-aware; HTML stripped, OCR tolerated)
        │
        ▼
  Tool 1  extract_structured   parse dose, pack, vegan/veg, B12/DHA/folate/D,
                               price(+market), claims — unit-aware, each value
                               carries its exact source snippet
        │
        ▼
  Tool 2  check_compliance     match each marketing claim against the EU/UK
                               health-claims reference (doc 08): compliant /
                               non-compliant / borderline, citing both snippets
        │
        ▼
  Tool 3  reconcile            group values by product+attribute (price by
                               market); highest-authority source is canonical;
                               disagreements → conflict; expected-but-absent →
                               "not found"; IU↔µg normalised so 25 µg ≡ 1000 IU
        │
        ▼
  cache → intelligence table + flags report

CHAT LOOP (per question, steps not one prompt)
  1 detect   which product(s) / attribute(s) the question targets
  2 retrieve top-k snippets from the vector store (never the whole corpus)
  3 gather   the reconciled structured facts + in-scope flags
  4 answer   Gemini phrases a cited answer from that evidence — or an extractive
             answer with no key. Missing fact → "not found", never a guess.
```

Every tool is a module: `extract.py`, `compliance.py`, `conflicts.py`,
`vectorstore.py`, orchestrated by `agent.py`.

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | status + which backends are active |
| `POST` | `/ingest` | (re)build the knowledge base |
| `POST` | `/query` | `{"question": "..."}` → cited answer + in-scope flags + step trace |
| `GET` | `/intelligence` | the structured table (product · attribute · value · source · confidence · flag) |
| `GET` | `/flags` | full flags report (conflicts · missing values · non-compliant claims · data-quality) |
| `GET` | `/examples` | the six sample questions (prompts only) |

---

## What breaks first at 10,000 documents, and what I'd change

**Breaks first:** re-embedding the entire corpus on every boot and the O(n) NumPy
cosine scan per query — both are linear in corpus size and hold everything in RAM.
**Change:** persist embeddings and move to an approximate-nearest-neighbour index
(FAISS or pgvector), embed incrementally at ingest, and turn conflict detection
from an in-process all-pairs group scan into a keyed aggregation in the datastore
(group by product+attribute in SQL), so reconciliation no longer requires loading
the whole corpus into one process.

---

## Repository layout

```
app/
  ingest.py       load + format-aware chunking
  embeddings.py   Gemini embeddings + TF-IDF fallback
  vectorstore.py  in-memory cosine retrieval
  extract.py      Tool 1 — deterministic structured extraction
  compliance.py   Tool 2 — claim vs health-claims reference
  conflicts.py    Tool 3 — reconcile conflicts/missing, build table + flags
  llm.py          Gemini chat wrapper (grounded, no beta features)
  agent.py        orchestrator: ingest pipeline + chat loop
  main.py         FastAPI surface + serves the frontend
frontend/index.html   chat box + intelligence table + flags report
data/             the 8 source documents + sources.json (provenance metadata)
tests/            end-to-end checks on the six questions + seeded traps
docs/             WORKFLOW, BUILD_AND_PRECISION (4-page), LOOM_SCRIPT
ANSWERS.md        the six briefing questions, precisely answered + flags report
```
