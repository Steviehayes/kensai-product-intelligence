# Submission email (draft)

**To:** karina@kensai.ai
**Subject:** Kensai take-home — product-intelligence agent (Steve Hayes)

---

Hi Karina,

Thank you — I genuinely enjoyed this one. It's a lovely miniature of the real
problem, and the seeded messiness made it a proper test.

Everything's here:

- **Live demo:** https://kensai-product-intelligence-441530711599.europe-west2.run.app
  (login: `kensai` / `Kensai-Review-2026`)
- **Repository:** https://github.com/Steviehayes/kensai-product-intelligence
- **Loom walkthrough (3–4 min):** [PASTE LOOM LINK]

**What it does.** It ingests the eight documents into a knowledge base (chunking +
embeddings + retrieval), then runs an agent in steps and tools — extract structured
product data → cross-check each claim against the EU/UK health-claims reference →
reconcile conflicts and gaps across sources → answer. Every answer and every table
cell traces to an exact source snippet; conflicts are flagged, and anything the
corpus doesn't contain comes back as "not found", never a guess. The stack is
deliberately light: FastAPI, a hand-rolled tool pipeline (no LangChain, so the
orchestration stays legible), and a single-file front end.

**The decision I'd most like to flag.** Extraction, compliance-checking and
conflict-detection are deliberately deterministic, not LLM-driven. On nutrient and
regulatory data you never want a model to quietly turn a µg into a mg or average two
conflicting figures — so every value is parsed with its unit and pinned to its source
line, and the language model is used only to phrase an answer from evidence it's
handed. It also means the intelligence table, the flags and the six answers are
correct with or without an API key.

**It caught the traps.** It surfaced ten issues, including the non-compliant "boosts
your immune system" claim on Ritual's UK listing; the MoleQlar B12 conflict (25 µg on
the datasheet, corroborated by its own 1000 % NRV, versus 500 µg on Amazon); and
Wellwoman being tagged "vegan: yes" at one retailer despite a gelatin capsule. It also
refuses to invent a figure the sources don't give — there's no official EU/UK price
for Ritual, so it says so — and it correctly does **not** flag Ritual's "25 µg /
1000 IU" Vitamin D as a conflict, because those are the same value.

In the repo you'll find one-command run steps, a short workflow write-up, a four-page
note on how it's built and why it's precise, and the six answers in `ANSWERS.md`. One
line on scale: at 10,000 documents the in-memory cosine scan and re-embedding on boot
break first — I'd move to a persistent ANN index (FAISS/pgvector) with incremental
embedding, and push conflict detection into the datastore.

Thanks again for putting this together — I'd love to talk it through.

Best wishes,
Steve

---

### Before you send — quick checklist
- [ ] **Record the Loom** using `docs/LOOM_SCRIPT.md`, then paste the link above.
- [ ] *(Optional but recommended)* Enable the Gemini chat on the live demo first, so
  open-ended questions are at their best — send me a free key from
  https://aistudio.google.com/apikey and I'll wire it in (~1 min).
- [ ] Confirm the login still works: the demo is `kensai` / `Kensai-Review-2026`.
