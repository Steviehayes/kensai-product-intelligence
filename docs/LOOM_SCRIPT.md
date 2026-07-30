# Loom script (3–5 minutes)

A tight walkthrough. Aim for signal, not jargon. Times are a guide.

**Live demo:** https://kensai-product-intelligence-441530711599.europe-west2.run.app
— login `kensai` / `Kensai-Review-2026` (Google Cloud Run; deterministic mode unless
a `GOOGLE_API_KEY` is set). Repo: https://github.com/Steviehayes/kensai-product-intelligence

---

**0:00 — What it is (20s)**
"This is a small product-intelligence agent for the Kensai take-home. It takes
eight messy, conflicting documents about three supplements and turns them into
clean, source-traceable intelligence — every answer and every table cell traces
back to an exact snippet, it flags conflicts, and it says 'not found' instead of
guessing. The documents are the source of truth, not the live sites."

**0:20 — Run it (20s)**
Show the terminal: `docker compose up`. "One command, zero config. It boots with
a deterministic layer that works even with no API key — so the table and the
answers are correct whether or not the LLM is switched on." Open
`http://localhost:8000`.

**0:40 — The intelligence table (50s)**
Scroll the table. "Product, attribute, value, confidence, and a flag. Click any
row and it shows the exact source line behind the value." Click the **MoleQlar
B12** row — show the conflict: 25 µg in the datasheet, 500 µg on Amazon. "It
doesn't average them or pick silently — it shows both, marks the datasheet value
canonical because it's higher authority *and* internally consistent at 1000 % NRV,
and raises a flag." Click **Ritual Vitamin D**: "25 µg and 1000 IU — those are the
same value, so it deliberately does *not* flag a conflict. Getting units right
cuts both ways."

**1:30 — Flags report (40s)**
Scroll to flags. "It auto-surfaced ten issues: the non-compliant Ritual immune
claim, the B12 conflict, Wellwoman being tagged vegan at one retailer despite a
gelatin capsule, missing values reported as 'not found', and data-quality notes on
the OCR datasheet and the undated blog."

**2:10 — Ask questions live (70s)**
Type two or three, including one of theirs:
- "Is Wellwoman suitable for vegans?" → No, gelatin, with the H&B conflict flagged.
- "How much B12 is in one MoleQlar capsule?" → the conflict, with both sources.
- One free-form question to show it isn't hardcoded.
"Notice the step trace under each answer — detect, retrieve, reconcile, answer.
It works in steps and tools, not one prompt."

**3:20 — Orchestration in 30s (30s)**
Show the repo tree briefly. "Four tools: extract, check-compliance, reconcile,
retrieve — orchestrated in `agent.py`. The key decision: extraction and
conflict-detection are deterministic, because on regulatory data you never want a
model silently changing a µg to a mg. The LLM only phrases the answer from evidence
it's handed."

**3:50 — Scale + close (20s)**
"At 10,000 documents the in-memory cosine scan and re-embedding on boot break
first — I'd move to FAISS or pgvector with incremental embedding and push conflict
detection into the datastore. Everything's in the README and a four-page write-up.
Thanks — enjoyed this one."
