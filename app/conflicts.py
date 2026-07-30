"""Reconciliation (agent tool #3): conflicts, missing values, and table build.

Groups every extracted value by product+attribute (price also by market), picks
the highest-authority value as canonical, and flags any source that disagrees.
Also emits explicit "not found" cells for expected-but-absent facts and
data-quality notes (OCR noise, undated source). The output is the structured
intelligence table plus the flags report.
"""

from __future__ import annotations

from .compliance import ClaimVerdict, REFERENCE_DOC_ID
from .extract import Extraction
from .ingest import DocMeta
from .schemas import Citation, Flag, IntelligenceCell

_AUTHORITY_RANK = {"high": 3, "medium": 2, "low": 1, "reference": 0}
_CONF = {"high": "high", "medium": "medium", "low": "low", "reference": "low"}

# Facts we expect to find for each product; anything absent becomes a "not found"
# cell rather than silently missing. (attribute, market-or-None)
EXPECTED = {
    "ritual": [("daily_dose", None), ("pack_size", None), ("vegan", None),
               ("b12", None), ("dha", None), ("price", "EU/UK")],
    "wellwoman": [("daily_dose", None), ("pack_size", None), ("vegan", None),
                  ("vegetarian", None), ("b12", None), ("price", "UK")],
    "moleqlar": [("daily_dose", None), ("pack_size", None), ("vegan", None),
                 ("b12", None), ("price", "EU")],
}
_PRETTY = {
    "daily_dose": "Recommended daily dose", "pack_size": "Pack size", "vegan": "Suitable for vegans",
    "vegetarian": "Suitable for vegetarians", "b12": "Vitamin B12 per capsule", "dha": "Omega-3 DHA",
    "folate": "Folate", "vitamin_d": "Vitamin D", "price": "Price",
}


def _cite(ex: Extraction, metas: dict[str, DocMeta]) -> Citation:
    m = metas[ex.doc_id]
    return Citation(doc_id=ex.doc_id, title=m.title, url=m.url, snippet=ex.snippet)


def _key(ex: Extraction):
    market = ex.market if ex.attribute == "price" else None
    return (ex.product, ex.attribute, market)


def _norm(ex: Extraction) -> str:
    """Comparable value for conflict detection (unit-normalised where relevant).

    Vitamin D is converted IU->µg (40 IU = 1 µg) so "25 µg" and "1000 IU" are
    recognised as the *same* value, not a false conflict.
    """
    if ex.attribute in {"b12", "dha", "folate", "vitamin_d"}:
        try:
            val = float(ex.value)
        except ValueError:
            return f"{ex.value}{ex.unit or ''}"
        unit = (ex.unit or "").lower()
        if ex.attribute == "vitamin_d" and unit == "iu":
            val, unit = val / 40.0, "µg"
        return f"{val:g}{unit}"
    return ex.value.strip().lower()


def _pretty(attr: str, market: str | None) -> str:
    label = _PRETTY.get(attr, attr)
    return f"{label} ({market})" if attr == "price" and market else label


def analyse(extractions, verdicts, metas_list):
    metas = {m.id: m for m in metas_list}
    groups: dict[tuple, list[Extraction]] = {}
    for ex in extractions:
        if ex.attribute.startswith("claim_"):
            continue
        groups.setdefault(_key(ex), []).append(ex)

    table: list[IntelligenceCell] = []
    flags: list[Flag] = []

    for (product, attribute, market), items in sorted(groups.items()):
        items.sort(key=lambda e: _AUTHORITY_RANK.get(e.confidence, 0), reverse=True)
        canonical = items[0]
        distinct = {_norm(e) for e in items}
        is_conflict = len(distinct) > 1
        citations = [_cite(e, metas) for e in items]

        table.append(IntelligenceCell(
            product=product,
            attribute=_pretty(attribute, market),
            value=canonical.value,
            unit=canonical.unit,
            confidence=_CONF.get(canonical.confidence, "low"),
            flag="conflict" if is_conflict else None,
            citations=citations,
        ))

        if is_conflict:
            values = ", ".join(f"{e.value}{(' ' + e.unit) if e.unit else ''} [{e.doc_id}]" for e in items)
            flags.append(Flag(
                kind="conflict", product=product, attribute=_pretty(attribute, market),
                summary=f"{product}: conflicting {_pretty(attribute, market)}",
                detail=f"Sources disagree ({values}). Canonical taken from the highest-authority "
                       f"source [{canonical.doc_id}].",
                citations=citations,
            ))

    _add_missing(table, flags, groups)
    _add_claim_rows(table, flags, verdicts, metas)
    _add_data_quality(flags, metas)
    return table, flags


def _add_missing(table, flags, groups):
    for product, expected in EXPECTED.items():
        for attribute, market in expected:
            if (product, attribute, market) in groups:
                continue
            table.append(IntelligenceCell(
                product=product, attribute=_pretty(attribute, market),
                value="Not found", unit=None, confidence="low", flag="missing", citations=[],
            ))
            flags.append(Flag(
                kind="missing_value", product=product, attribute=_pretty(attribute, market),
                summary=f"{product}: {_pretty(attribute, market)} not stated in any source",
                detail="No source in the corpus provides this value; reported as 'not found' "
                       "rather than guessed.",
                citations=[],
            ))


def _add_claim_rows(table, flags, verdicts: list[ClaimVerdict], metas):
    ref = metas.get(REFERENCE_DOC_ID)
    best: dict[str, ClaimVerdict] = {}
    rank = {"non_compliant": 2, "compliant": 1, "borderline": 0}
    for v in verdicts:  # keep the most decisive verdict per product
        if v.product not in best or rank[v.verdict] > rank[best[v.product].verdict]:
            best[v.product] = v

    for product, v in best.items():
        src = metas[v.doc_id]
        cites = [Citation(doc_id=v.doc_id, title=src.title, url=src.url, snippet=v.claim_text)]
        if ref and v.reference_snippet:
            cites.append(Citation(doc_id=ref.id, title=ref.title, url=ref.url, snippet=v.reference_snippet))
        table.append(IntelligenceCell(
            product=product, attribute="Health claim compliance",
            value=f"{v.verdict.replace('_', '-')}: “{v.claim_text}”",
            unit=None,
            confidence="high",
            flag="compliance" if v.verdict != "compliant" else None,
            citations=cites,
        ))
        if v.verdict == "non_compliant":
            flags.append(Flag(
                kind="non_compliant_claim", product=product, attribute="Health claim compliance",
                summary=f"{product}: non-compliant health claim",
                detail=f"“{v.claim_text}” — {v.reason}",
                citations=cites,
            ))


def _add_data_quality(flags, metas):
    quality = [
        ("05_moleqlar_datasheet",
         "OCR artefacts in the datasheet (e.g. 'Vitam1n B12', 'ug' for µg, 'taglich'). "
         "Values read through the noise but the source is imperfect."),
        ("07_comparison_review",
         "Undated blog review — recency unknown and it self-notes formulas/prices change, "
         "so its figures (e.g. ~320 mg DHA) are treated as low-confidence/historical."),
    ]
    for doc_id, detail in quality:
        m = metas.get(doc_id)
        if not m:
            continue
        flags.append(Flag(
            kind="data_quality", product=None, attribute=None,
            summary=f"Data-quality note on [{doc_id}]", detail=detail,
            citations=[Citation(doc_id=doc_id, title=m.title, url=m.url, snippet=m.title)],
        ))
