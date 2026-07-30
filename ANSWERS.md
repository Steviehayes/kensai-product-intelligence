# Answers — Kensai Product Intelligence Take-Home

Every answer below is produced by the agent and traced to an exact source
snippet. Where the corpus disagrees, the conflict is surfaced rather than hidden;
where the corpus is silent, the answer is "not found" rather than a guess.
The documents — not the live websites — are the source of truth.

Document key: `01` Ritual official · `02` Ritual Amazon.co.uk · `03` Wellwoman
official · `04` Wellwoman Holland & Barrett · `05` MoleQlar datasheet (OCR) ·
`06` MoleQlar Amazon.de · `07` comparison blog (undated) · `08` EU/UK health-claims
reference.

---

### 1. Recommended daily dose and pack size of Vitabiotics Wellwoman Original, with the original source

**One capsule per day; pack of 30 capsules.** The two sources agree on both.

- `03` (manufacturer, vitabiotics.com): *"30 capsules · 1 capsule per day (30-day supply)"*
- `04` (Holland & Barrett): *"Pack size: 30 Capsules"* and *"Directions: One capsule per day with your main meal"*

**Original source:** the manufacturer page, **https://vitabiotics.com/products/wellwoman**.

*(Note: the two sources conflict on price — £8.95 official vs £7.99 at H&B — which is flagged separately, though price is not asked here.)*

---

### 2. Is Ritual Essential for Women vegan?

**Yes — it is vegan.** All three sources that mention it agree.

- `01` (manufacturer): *"Vegan · gluten-free · non-GMO · sugar-free"* and *"60 vegan capsules"*
- `02` (Amazon.co.uk): *"Suitable for vegans"*
- `07` (blog): *"Ritual: sleek, genuinely vegan, nice methylated forms."*

---

### 3. How much Vitamin B12 is in one capsule of MoleQlar Vitamin B Komplex?

**The sources conflict — this is flagged, not resolved silently.**

- `05` (official datasheet, OCR): *"Vitam1n B12 (Methylcobalam1n) .......... 25 ug (1000% NRV)"* → **25 µg**
- `06` (Amazon.de listing): *"Vitamin B12: 500 µg pro Kapsel (methylcobalamin)"* → **500 µg**

**Higher-confidence value: 25 µg.** It comes from the official datasheet (higher
authority than a marketplace listing) **and it is internally consistent**: the B12
Nutrient Reference Value is 2.5 µg, so 25 µg = 1000 % NRV, exactly as the datasheet
states. 500 µg would be 20,000 % NRV, which no source supports. The agent reports
**25 µg with the conflict raised**, and does not silently discard the 500 µg figure.

---

### 4. Is Vitabiotics Wellwoman Original suitable for vegans?

**No — it is not suitable for vegans.** The capsule shell is animal-derived gelatin.

- `03` (manufacturer): *"Capsule shell: Pharmaceutical-grade GELATIN (Halal bovine source)"* and *"Suitable for vegetarians: NO (contains gelatin)"*
- `07` (blog): *"the capsule is gelatin, so it is NOT suitable for vegans or vegetarians despite what some shops tag it as."*

**Conflict flagged:** `04` (Holland & Barrett) lists *"Suitable for Vegans: Yes"*
and *"Suitable for Vegetarians: Yes"*. This contradicts the gelatin capsule and is
a **retailer mislabelling** — the blog even calls it out ("despite what some shops
tag it as"). The agent takes the manufacturer as canonical (No) and raises the
conflict against the H&B listing.

---

### 5. The UK listing for Ritual claims it "boosts your immune system." Is that compliant for the EU/UK market? Why?

**No — it is not compliant.**

- The claim appears in `02` (Amazon.co.uk): *"Clinically-backed daily multivitamin that BOOSTS YOUR IMMUNE SYSTEM…"*
- `08` (health-claims reference) lists it **explicitly** under *NOT permitted*: *"'Boosts your immune system' (vague/absolute; not the authorised wording)"*.

**Why:** under EU Regulation (EC) No 1924/2006 (and the mirror GB register) only the
**exact authorised wording**, with the conditions of use met, may be printed.
"Boosts your immune system" is vague and absolute — it is not on the register. The
permitted route is the specific, nutrient-linked wording, e.g. *"Vitamin D
contributes to the normal function of the immune system."* As the reference notes,
being scientifically plausible does **not** make a claim legal to print.

---

### 6. What is the official EU/UK retail price of Ritual Essential for Women?

**Not found — no official EU/UK retail price is published in the corpus.** Reported
as "not found", not guessed.

- `01` (manufacturer): *"EU / UK price: not published. No EU/UK-specific label or importer listed."*
- `02` (Amazon.co.uk): *"Price: Currently unavailable. We don't deliver this item to your address."*
- `07` (blog): *"I could not find an official EU or UK price for Ritual anywhere — it seems US-only for now."*

The only price given anywhere is the **US direct price of $39.00** (`01`), which is
not an EU/UK retail price.

---

### Stretch — which products are both vegan and may legally carry an EU "energy metabolism" claim?

**Ritual and MoleQlar.**

The authorised energy-metabolism claim is *"Vitamin B12 contributes to normal
energy-yielding metabolism"* (`08`), permitted only where the product contains a
**significant amount** of B12 (≥ 15 % NRV = ≥ 0.375 µg).

- **Ritual** — vegan (`01`), B12 **8 µg** (`01`) = 320 % NRV → qualifies.
- **MoleQlar** — vegan (`05`/`06`), B12 **25 µg** (`05`) = 1000 % NRV → qualifies, and
  already uses the authorised wording on `06`: *"Supports normal energy metabolism and
  normal function of the nervous system."*
- **Wellwoman** — excluded: it contains B12 but is **not vegan** (gelatin capsule).

---

## Flags report (auto-surfaced)

The agent detected **10 issues** across the corpus. Conflicts show the canonical
(highest-authority) value; nothing is silently dropped.

**Non-compliant claim (1)**
1. **Ritual — "boosts your immune system"** (`02`) violates the health-claims
   reference (`08`). Not authorised wording.

**Conflicts (6)**
2. **MoleQlar B12** — 25 µg (`05`, datasheet, corroborated by 1000 % NRV) vs 500 µg (`06`).
3. **MoleQlar price** — €24,90 (`05`) vs €19,99 (`06`).
4. **Ritual Omega-3 DHA** — 330 mg (`01`) vs 300 mg (`02`) vs ~320 mg (`07`, historical/older formulation).
5. **Wellwoman price** — £8.95 (`03`) vs £7.99 (`04`).
6. **Wellwoman vegan** — No / gelatin (`03`, `07`) vs "Suitable for Vegans: Yes" (`04`, mislabelled).
7. **Wellwoman vegetarian** — No (`03`) vs Yes (`04`).

**Missing value (1)**
8. **Wellwoman B12 amount** — `03` lists Vitamin B12 (as cyanocobalamin) but gives
   no quantity; no source states it. Reported as "not found".

**Data-quality notes (2)**
9. **`05` MoleQlar datasheet** — OCR artefacts ("Vitam1n B12", "ug" for µg,
   "taglich"). Values were read through the noise, but the source is imperfect.
10. **`07` comparison blog** — undated; it self-notes that formulas and prices
    change, so its figures (e.g. ~320 mg DHA) are treated as low-confidence/historical.

**A precision detail worth noting:** Ritual's Vitamin D is stated as *"25 µg (1000
IU)"* (`01`) and *"1000 IU"* (`02`). A naïve system flags these as a conflict; they
are the **same value** (40 IU = 1 µg, so 1000 IU = 25 µg). The agent normalises
IU↔µg and correctly reports **no conflict** — the kind of false positive that unit
precision exists to avoid.
