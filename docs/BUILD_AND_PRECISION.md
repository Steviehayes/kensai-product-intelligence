# How this application was built, and why it is precise

*A four-page summary for the Kensai take-home.*

---

## 1. The problem

Kensai turns messy, multi-source product and regulatory data into clean,
trustworthy, source-traceable intelligence. This exercise is a miniature of that:
eight documents about three real EU/UK supplements, in five formats (Markdown,
plain text, HTML, an OCR'd PDF extract, and a health-claims reference), deliberately
seeded with conflicts, gaps and at least one non-compliant claim. The task is not
to *know* about supplements — it is to read carefully, get the units right, cite the
exact snippet, surface every discrepancy, and refuse to guess.

That framing drove every engineering decision below. The measure of success is not
"does it answer the six questions" — a lookup table could do that. It is "does it
answer *precisely, traceably and honestly*, and would it still behave when the
graders ask their own questions." So the system is built as a genuine
extract → cross-check → reconcile → answer pipeline, with provenance as its spine.

---

## 2. Architecture at a glance

The application is a single FastAPI service that serves both a small JSON API and a
one-file frontend, so the whole thing is one container and one command to run. It
has two phases:

- **Ingest** (once, at start-up) builds a reconciled knowledge base and caches it.
- **Query** (per question) retrieves from that base and phrases an answer.

The stack is deliberately light: **FastAPI** for the backend; a **hand-rolled tool
pipeline** rather than an agent framework, so the orchestration is legible; an
**in-memory NumPy vector store** because the corpus is eight documents and a vector
database would be theatre; **Google Gemini's free tier** for embeddings and chat;
and a **scikit-learn TF-IDF fallback** so the app boots and answers with no API key
at all. The frontend is one HTML file — a chat box, the structured intelligence
table, and the flags report — with no build step.

I chose *not* to reach for LangChain or LlamaIndex. For a task whose entire point is
attention to detail and legible orchestration, a framework would hide the four
steps behind abstractions and make it harder, not easier, to see exactly how a
value reached the screen. Each tool here is a small, readable module.

---

## 3. The decision that matters most: determinism where correctness is non-negotiable

The single most important design choice is that **extraction, compliance-checking
and conflict-detection are deterministic, not LLM-driven.** The language model is
used only to *phrase* an answer from evidence it is handed — never as a source of
facts.

The reasoning is specific to this domain. On nutrient and regulatory data, the
failure modes of an LLM are exactly the ones that matter here: silently turning a µg
into a mg, "helpfully" averaging two conflicting figures, or filling a gap with a
plausible number. Those are not hypothetical — they are the traps the corpus is
built from. A deterministic parser that pins every figure to the exact source line
cannot do any of those things. It can be wrong in visible, testable ways (a regex
misses), but it cannot hallucinate a confident falsehood.

So the division of labour is: **deterministic tools produce the intelligence table,
the flags and the six answers** — correct and reproducible, with or without an API
key — and **the LLM handles open-ended phrasing** for the graders' own questions,
strictly grounded in retrieved snippets and the already-reconciled facts, and
instructed to say "not found" rather than invent. Determinism where correctness is
non-negotiable; the model where flexibility is.

---

## 4. How precision is engineered

Six concrete mechanisms make the output precise rather than merely plausible.

**Unit-aware extraction.** Nutrient amounts are parsed with the unit as a separate,
first-class field (µg / mg / IU), never folded into the number. The regexes anchor
on a trailing unit, so a stray "1000 %" in "25 ug (1000% NRV)" is skipped and only
"25 µg" is captured. OCR variants are handled explicitly — "ug" is read as µg,
"Vitam1n" as Vitamin — and the extractor's gap pattern is allowed to cross the
datasheet's dot-leaders (`..........`) that a naïve pattern would stop at.

**IU ↔ µg normalisation — avoiding a *false* conflict.** Ritual's Vitamin D is
"25 µg (1000 IU)" in one source and "1000 IU" in another. These are the *same
value* (40 IU = 1 µg). A system that only compares strings would raise a spurious
conflict here. The reconciler converts IU to µg before comparing, and correctly
reports no conflict. Precision is as much about *not* flagging false positives as
catching real ones.

**Provenance as the primary data structure.** Every extracted value is an object
that carries its exact source snippet. That object flows unchanged into table cells,
flags and chat citations. The consequence is structural: it is not possible for the
UI to display a value without also being able to show the line it came from. Nothing
is asserted without a citation.

**Authority ranking for canonical selection.** Sources are ranked — manufacturer >
retailer/marketplace > undated blog. When a group of values disagrees, the
highest-authority source becomes the canonical answer, and the disagreement is
raised as a conflict listing *every* source. This is why the agent reports Wellwoman
as "not vegan" (manufacturer, gelatin capsule) while explicitly flagging the Holland
& Barrett listing that wrongly tags it vegan.

**Conflicts are surfaced, never silently resolved.** When the MoleQlar B12 figure is
25 µg in the datasheet and 500 µg on Amazon, the agent does not pick one and move
on. It reports the canonical value *and* raises a conflict that shows both figures
with their sources — and, in the answer, notes that 25 µg is corroborated by its own
"1000 % NRV" arithmetic while 500 µg is not. The reviewer sees the discrepancy and
the reasoning, not a laundered single number.

**Honest "not found" for gaps.** Where the corpus is silent — Ritual's official
EU/UK price, Wellwoman's B12 quantity — the agent returns "not found" and raises a
missing-value flag, rather than guessing. This is enforced structurally (expected
attributes with no extraction become explicit "not found" cells) and, on the LLM
path, by instruction.

Underpinning all six: **format-aware ingestion.** HTML is stripped to readable
label/value lines; the OCR datasheet is tolerated; and multi-product documents are
split line-by-line and each line attributed to the product it names, so a Ritual
number is never mis-read as a MoleQlar one.

---

## 5. The seeded traps, and how each was caught

| Trap in the corpus | How the agent handles it |
| --- | --- |
| MoleQlar B12: **25 µg** (datasheet) vs **500 µg** (Amazon) | Conflict raised; 25 µg canonical (higher authority + internally consistent at 1000 % NRV) |
| Wellwoman tagged **"vegan: Yes"** at H&B, but capsule is **gelatin** | Reported "No" (manufacturer); H&B listing flagged as a mislabelling conflict |
| Ritual **"boosts your immune system"** | Matched to the reference's *not-permitted* list → non-compliant, with the reason |
| Ritual DHA **330 / 300 / ~320 mg** across three sources | Conflict raised; 330 mg canonical; blog's ~320 mg noted as historical/low-confidence |
| Ritual Vitamin D **25 µg** vs **1000 IU** | Recognised as the *same* value (IU→µg) — deliberately *not* flagged |
| Ritual official **EU/UK price** absent | "Not found"; only the US $39.00 is reported, and it is labelled US |
| Wellwoman **B12 quantity** never stated | "Not found" + missing-value flag |
| Prices differ by market (£8.95/£7.99; €24,90/€19,99) | Real conflicts within a market are flagged; cross-market prices are not conflated |
| **OCR noise** and an **undated** blog | Two data-quality flags; blog figures down-weighted to low confidence |

An automated test suite asserts each of these, so a future change that breaks one is
caught immediately rather than shipped.

---

## 6. Graceful degradation

The app is designed so a reviewer can run one command and see real output with no
setup. Without an API key it uses TF-IDF retrieval and the deterministic answer
layer — the table, the flags and the six answers all work. Adding a free Gemini key
(one line in `.env`) upgrades retrieval to real embeddings and enables full
natural-language chat for arbitrary questions. The same image runs locally, under
Docker, and on Google Cloud Run unchanged, because behaviour is driven entirely by
environment variables — including an optional HTTP Basic Auth gate (`APP_USER` /
`APP_PASSWORD`) that protects the public demo without a line of code changing.

---

## 7. Limitations, stated honestly

The deterministic extractor is tuned to the *shape* of supplement product pages
(nutrient lines, dose/pack phrasing, price formats); it generalises to similar
documents but is not a universal parser, and a genuinely novel layout would need a
new pattern or an LLM-assisted extraction pass. The offline extractive answer is
intentionally literal — it lists the reconciled facts rather than composing prose;
the natural-language path (with a key) is the one meant for open-ended questions.
And the compliance check covers the wording rules in the supplied reference, not the
full EU/GB registers. None of these are hidden — they are the honest edges of a
two-to-four-hour build, and each has an obvious next step.

---

## 8. What breaks first at 10,000 documents

Two things, both linear in corpus size: re-embedding the entire corpus on every
start-up, and the O(n) NumPy cosine scan per query, which holds every vector in RAM.
The fix is to persist embeddings and move to an approximate-nearest-neighbour index
(FAISS or pgvector), embed incrementally at ingest, and turn conflict detection from
an in-process all-pairs group scan into a keyed aggregation in the datastore — group
by product and attribute in SQL — so reconciliation no longer requires loading the
whole corpus into a single process. The tool interfaces (`add`/`search`,
`extract`/`reconcile`) are already shaped so those swaps are internal.

---

## 9. In one line

The system is precise because it refuses to let a language model near the numbers:
every figure is parsed with its unit, pinned to its source line, ranked by
authority, checked for conflict, and reported honestly — including "not found" — so
that every answer and every cell can be traced back to exactly where it came from.
