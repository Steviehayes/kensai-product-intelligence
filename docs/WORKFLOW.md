# Workflow — how the agent works

This document traces one full pass through the system: from eight raw files to a
cited answer on screen. It is deliberately concrete — every box below maps to a
module you can open.

---

## 1. The two phases

The agent has an **ingest phase** (runs once, when the server starts) and a
**query phase** (runs per question). Ingest builds a reconciled knowledge base and
caches it; queries read from it. Nothing is recomputed per request except
retrieval and phrasing.

```
                        ┌──────────────────────── INGEST (startup) ───────────────────────┐
  data/ (8 docs) ──▶ load+chunk ──▶ embed ──▶ Tool1 extract ──▶ Tool2 compliance ──▶ Tool3 reconcile ──▶ cache
                        │             │                                                     │
                        │             └── vector store (retrieval)                          └── table + flags
                        └── format-aware: HTML stripped, OCR tolerated, provenance attached

                        ┌──────────────────────── QUERY (per question) ───────────────────┐
  question ──▶ detect product/attribute ──▶ retrieve top-k ──▶ gather facts+flags ──▶ answer (Gemini | extractive) ──▶ cited response
```

---

## 2. Ingest, step by step

**Load + chunk (`ingest.py`).** Each document is read with its format in mind:
Markdown and text pass through; the Holland & Barrett file is real HTML and is
stripped to readable `label: value` lines; the MoleQlar datasheet is an OCR
extract and is left intact so the dot-leaders and artefacts can be handled
downstream. Text is split on blank lines into small chunks (~600 chars), and a
single fact line is never split mid-line, so a retrieved snippet is always a
complete, quotable statement. Every chunk carries its `doc_id`, title, URL,
product(s), market and authority.

**Embed (`embeddings.py` + `vectorstore.py`).** Chunks are embedded — with Google
`text-embedding-004` when a key is present, otherwise scikit-learn TF-IDF — and
stored in an in-memory NumPy matrix for cosine search. The interface is `add()` /
`search(query, top_k, product)`.

**Tool 1 — `extract_structured` (`extract.py`).** Unit-aware regexes pull a fixed
attribute set per product: daily dose, pack size, vegan/vegetarian status, Vitamin
B12 / DHA / folate / Vitamin D amounts, price (tagged by market), and verbatim
marketing claims. Two details matter:
- **Multi-product documents** (the blog) are split line-by-line and each line
  attributed to the product it names, so a Ritual figure is never read as a
  MoleQlar one.
- **The value's exact source line is captured** as the snippet, and a unit is kept
  separately (µg / mg / IU), never conflated.

**Tool 2 — `check_compliance` (`compliance.py`).** Each extracted claim is matched
against the EU/UK health-claims reference (document 08). "Boosts your immune
system" is matched to the reference's *not-permitted* list → **non-compliant**; the
authorised energy/nervous-system wording → **compliant**; anything else → 
**borderline**. Every verdict cites two snippets: the claim as printed and the
reference line that decides it.

**Tool 3 — `reconcile` (`conflicts.py`).** Extractions are grouped by
product + attribute (price also by market). Within a group:
- the **highest-authority** source (manufacturer > retailer/marketplace > blog)
  becomes the canonical value;
- if the group holds more than one distinct value, a **conflict** flag is raised
  listing every source;
- units are normalised for comparison — Vitamin D IU is converted to µg, so
  "25 µg" and "1000 IU" are recognised as identical, not a false conflict.

Then expected-but-absent facts become **"not found"** cells with a
**missing-value** flag, and two **data-quality** notes are added (the OCR datasheet
and the undated blog). The result — the intelligence table and the flags report —
is cached.

---

## 3. Query, step by step (`agent.py`)

1. **Detect.** Cheap keyword rules identify which product(s) and attribute(s) the
   question is about. This scopes retrieval and picks the right structured facts.
2. **Retrieve.** The vector store returns the top-k relevant snippets — never the
   whole corpus — optionally filtered to the detected product.
3. **Gather.** The reconciled structured facts and in-scope flags for that product
   are collected. This is what keeps answers grounded: the model is handed values
   that have *already* been cross-checked.
4. **Answer.** With a key, Gemini is given the question, the reconciled facts and
   the retrieved snippets, and told to answer *only* from them, quote units
   exactly, surface conflicts and say "not found" if absent. Without a key, an
   extractive answer is composed directly from the structured facts. Either way the
   response carries its citations, the in-scope flags, and a short trace of the
   steps the agent ran.

---

## 4. Where provenance lives

Provenance is not bolted on at the end — it is the primary data structure. Every
extracted value is an object with its source snippet; every table cell carries a
list of citations; every flag carries the snippets that triggered it; every chat
answer returns the citations behind it. It is not possible for the UI to show a
value without also being able to show where it came from.
