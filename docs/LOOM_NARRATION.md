# Loom narration — read aloud, ~3.5 minutes

Log in to the live demo first, start the Loom recording, then read the **spoken**
lines while doing the bracketed **[ACTION]** cues. One take is fine — small stumbles
are normal and human.

Live demo: https://kensai-product-intelligence-441530711599.europe-west2.run.app
Login: `kensai` / `Kensai-Review-2026`

---

**[ACTION: the app is on screen, already logged in]**

"Hi — this is a small product-intelligence agent I built for the Kensai take-home.
The problem it solves is the one you described: eight messy, conflicting documents
about three supplements, and the job is to turn them into clean intelligence you can
actually trust — where every answer traces back to an exact source, conflicts are
flagged, and it never guesses.

**[ACTION: gesture at the layout]** On the right is the structured intelligence
table — product, attribute, value, the source it came from, a confidence level, and
a flag. On the left is the chat box. Let me show you the detail first, because that's
really the point of this exercise.

**[ACTION: click the MoleQlar 'Vitamin B12 per capsule' row to expand it]** Here's
Vitamin B12 for MoleQlar. The datasheet says 25 micrograms; the Amazon listing says
500. The agent doesn't average them or quietly pick one — it shows both with their
exact snippets, marks the datasheet value canonical because it's higher-authority
and internally consistent at a thousand percent NRV, and raises a conflict flag.

**[ACTION: click the Ritual 'Vitamin D' row]** And here's the flip side. Ritual's
Vitamin D reads 25 micrograms in one source and 1000 IU in another. Those are the
same value — so it deliberately does *not* flag a conflict. Getting the units right
cuts both ways.

**[ACTION: scroll to the flags report]** Down here it auto-surfaced ten issues. The
non-compliant claim you seeded — Ritual's UK listing says it 'boosts your immune
system', which the health-claims reference explicitly lists as not-permitted wording.
The B12 conflict. Wellwoman tagged 'suitable for vegans' at one retailer even though
its capsule is gelatin. Values that simply aren't in the documents, reported as 'not
found'. And data-quality notes on the OCR'd datasheet and the undated blog.

**[ACTION: type into the chat — 'Is Wellwoman suitable for vegans?' — and send]** Let
me ask it a couple of things. Is Wellwoman suitable for vegans? … No — because of the
gelatin capsule, and it flags the retailer that got it wrong.

**[ACTION: type — 'How much B12 is in one MoleQlar capsule?' — and send]** How much
B12 in a MoleQlar capsule? … It gives the conflict, both figures, both sources.

**[ACTION: point at the 'steps' line under the answer]** And notice this trace under
each answer — detect, retrieve, reconcile, answer. It works in steps and tools, not
a single prompt.

**[ACTION: switch to the GitHub repo tab]** Quickly, on how it's built: four tools —
extract, check-compliance, reconcile, and retrieve — orchestrated in agent.py. The
decision I care most about is that the extraction and conflict-detection are
deterministic, not the language model, because on regulatory data you never want a
model silently turning a microgram into a milligram. The model is only used to phrase
an answer from evidence it's handed.

**[ACTION: wrap up]** Last thing — at ten thousand documents, the in-memory search
and re-embedding on startup break first; I'd move to a proper vector index like FAISS
or pgvector with incremental embedding. There's a README with one-command run steps
and a four-page write-up in the repo. Thanks so much — I really enjoyed this one."

---

### Tips
- **One take is fine.** If you fluff a line, pause and say it again — Loom lets you
  trim, or just leave it; it reads as genuine.
- Keep it under 5 minutes (the free Loom limit). This script runs ~3.5.
- Speak a touch slower than feels natural; it always sounds better on playback.
- When done: copy the **Share link** and paste it into the email (`[PASTE LOOM LINK]`).
