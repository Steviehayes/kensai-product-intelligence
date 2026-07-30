"""End-to-end checks on the deterministic layer (no API key required).

These assert the seeded traps are caught and the 6 briefing questions resolve
correctly, independent of any LLM. Run: `pytest -q`.
"""

from app.agent import KnowledgeBase


def build():
    kb = KnowledgeBase()
    kb.build()
    return kb


def cell(kb, product, attr_prefix):
    return next(c for c in kb.table if c.product == product and c.attribute.startswith(attr_prefix))


def flag_kinds(kb, product=None):
    return [(f.kind, f.attribute) for f in kb.flags if product is None or f.product == product]


def test_q1_wellwoman_dose_and_pack():
    kb = build()
    assert cell(kb, "wellwoman", "Recommended daily dose").value.startswith("1")
    assert cell(kb, "wellwoman", "Pack size").value == "30"
    # original source is the manufacturer page
    cites = cell(kb, "wellwoman", "Pack size").citations
    assert any(c.doc_id == "03_wellwoman_official" for c in cites)


def test_q2_ritual_vegan_yes():
    kb = build()
    assert cell(kb, "ritual", "Suitable for vegans").value == "Yes"


def test_q3_moleqlar_b12_conflict():
    kb = build()
    c = cell(kb, "moleqlar", "Vitamin B12 per capsule")
    assert c.flag == "conflict"
    snippets = " ".join(x.snippet for x in c.citations)
    assert "25" in snippets and "500" in snippets  # both values surfaced


def test_q4_wellwoman_not_vegan_but_conflicted():
    kb = build()
    c = cell(kb, "wellwoman", "Suitable for vegans")
    assert c.value == "No"          # canonical from official (gelatin)
    assert c.flag == "conflict"     # H&B wrongly says vegan: yes


def test_q5_ritual_immune_claim_non_compliant():
    kb = build()
    assert any(k == "non_compliant_claim" for k, _ in flag_kinds(kb, "ritual"))


def test_q6_ritual_eu_uk_price_not_found():
    kb = build()
    c = cell(kb, "ritual", "Price (EU/UK)")
    assert "Not published" in c.value or c.value == "Not found"


def test_flags_include_dha_conflict():
    kb = build()
    assert any(k == "conflict" and a and a.startswith("Omega-3 DHA") for k, a in flag_kinds(kb, "ritual"))


def test_stretch_vegan_and_b12_products():
    kb = build()
    vegan = {c.product for c in kb.table if c.attribute.startswith("Suitable for vegans") and c.value == "Yes"}
    has_b12 = {c.product for c in kb.table
               if c.attribute.startswith("Vitamin B12") and c.value not in ("Not found",)}
    qualifies = vegan & has_b12
    assert "ritual" in qualifies and "moleqlar" in qualifies and "wellwoman" not in qualifies
