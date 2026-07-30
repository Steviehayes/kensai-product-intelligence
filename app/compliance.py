"""Claim compliance check (agent tool #2).

Takes the verbatim marketing/health claims pulled by the extractor and checks
each against the EU/UK health-claims reference (document 08). A verdict always
cites two snippets: the claim as printed, and the reference line that decides it.

Rule of thumb from the reference itself: only the *exact authorised wording*
(with conditions met) is permitted; vague/absolute wording like "boosts your
immune system" is not — scientific plausibility is irrelevant to legality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .extract import Extraction
from .ingest import DocMeta

REFERENCE_DOC_ID = "08_health_claims_reference"


@dataclass
class ClaimVerdict:
    product: str
    doc_id: str
    claim_text: str
    verdict: str  # "compliant" | "non_compliant" | "borderline"
    reason: str
    reference_snippet: str


def _find_line(text: str, pattern: str) -> str:
    m = re.search(pattern, text, re.I)
    if not m:
        return ""
    ls = text.rfind("\n", 0, m.start()) + 1
    le = text.find("\n", m.end())
    if le == -1:
        le = len(text)
    return re.sub(r"\s+", " ", text[ls:le]).strip().lstrip("- ")


def assess_claims(extractions: list[Extraction], reference_text: str) -> list[ClaimVerdict]:
    banned_immune = _find_line(reference_text, r"boosts your immune system")
    authorised_energy = _find_line(reference_text, r"energy-yielding metabolism")
    authorised_immune = _find_line(reference_text, r"immune system")  # the vitamin D wording

    verdicts: list[ClaimVerdict] = []
    seen: set[tuple] = set()

    for ex in extractions:
        if ex.attribute not in {"claim_immune", "claim_energy"}:
            continue
        text = ex.value
        low = text.lower()
        key = (ex.product, ex.doc_id, text)
        if key in seen:
            continue
        seen.add(key)

        if re.search(r"boost\w*\b.*\bimmune", low):
            verdicts.append(ClaimVerdict(
                ex.product, ex.doc_id, text, "non_compliant",
                "\"Boosts your immune system\" is vague/absolute wording that is not on the "
                "authorised register. The permitted immune wording is the specific "
                "\"Vitamin D contributes to the normal function of the immune system\".",
                banned_immune,
            ))
        elif re.search(r"energy[- ]?yielding|energy metabolism|energiestoffwechsel|nervous system|normal function of the immune system", low):
            verdicts.append(ClaimVerdict(
                ex.product, ex.doc_id, text, "compliant",
                "Matches the authorised energy/nervous-system wording for Vitamin B12 "
                "(permitted only where the product contains a significant amount of B12).",
                authorised_energy,
            ))
        else:
            verdicts.append(ClaimVerdict(
                ex.product, ex.doc_id, text, "borderline",
                "General immune 'support/function' wording — not the banned 'boosts', but "
                "must use the exact authorised phrasing tied to a qualifying nutrient.",
                authorised_immune,
            ))
    return verdicts
