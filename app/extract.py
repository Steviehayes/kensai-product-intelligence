"""Deterministic structured extraction (agent tool #1).

Parses each product document for a fixed set of attributes (dose, pack size,
vegan status, nutrient amounts, price, marketing claims) using unit-aware
regexes, and attaches the exact source line to every value. This layer is
intentionally *not* LLM-driven: on regulatory/nutrient data you want a µg to
stay a µg, reproducibly, and every number to be traceable to a quoted line.

It generalises by pattern, not by hardcoded answers — point it at another
supplement page of similar shape and it extracts the same attributes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ingest import DocMeta

PRODUCT_KEYWORDS = {
    "ritual": ["ritual"],
    "wellwoman": ["wellwoman", "well woman", "vitabiotics"],
    "moleqlar": ["moleqlar"],
}
_WORD_NUM = {"one": "1", "two": "2", "three": "3", "eine": "1", "ein": "1"}


@dataclass
class Extraction:
    product: str
    attribute: str
    value: str
    unit: str | None
    doc_id: str
    snippet: str
    confidence: str
    market: str | None = None


def _snippet(text: str, start: int, end: int) -> str:
    ls = text.rfind("\n", 0, start) + 1
    le = text.find("\n", end)
    if le == -1:
        le = len(text)
    return re.sub(r"\s+", " ", text[ls:le]).strip()


def _norm_unit(u: str) -> str:
    u = u.lower()
    if u in {"ug", "mcg", "µg"}:
        return "µg"
    return u


def _segments(meta: DocMeta, text: str) -> list[tuple[str, str, int]]:
    """Return (product, segment_text, offset) pairs.

    Single-product docs pass through whole. The multi-product blog is split by
    line and each line attributed to the product it names, so a Ritual number is
    never mis-attributed to MoleQlar.
    """
    if len(meta.products) == 1:
        return [(meta.products[0], text, 0)]
    segs: list[tuple[str, str, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        low = line.lower()
        for product, kws in PRODUCT_KEYWORDS.items():
            if product in meta.products and any(k in low for k in kws):
                segs.append((product, line, offset))
                break
        offset += len(line)
    return segs


def _add(out, product, attr, value, unit, meta, seg_text, m, offset, conf=None, market=None):
    out.append(
        Extraction(
            product=product,
            attribute=attr,
            value=value,
            unit=unit,
            doc_id=meta.id,
            snippet=_snippet(seg_text, m.start(), m.end()),
            confidence=conf or meta.authority,
            market=market or meta.market,
        )
    )


def _extract_segment(product: str, meta: DocMeta, text: str, offset: int, out: list):
    low = text.lower()

    # pack size ---------------------------------------------------------------
    for m in re.finditer(r"(\d{2,3})\s*(?:vegane?\s+)?(?:capsules?|kapseln|caps|tablets?)\b", text, re.I):
        _add(out, product, "pack_size", m.group(1), "capsules", meta, text, m, offset)

    # daily dose --------------------------------------------------------------
    # gap forbids digits so "30 capsules · 1 capsule per day" reads the dose (1),
    # not the pack count (30).
    dose_re = r"(\d+|one|two|three)\s*(?:vegan\s+)?(?:capsules?|kapsel|tablets?)[^.\n\d]{0,25}?(?:per day|daily|t[aä]glich|a day)"
    for m in re.finditer(dose_re, text, re.I):
        n = _WORD_NUM.get(m.group(1).lower(), m.group(1))
        label = f"{n} capsule per day" if n == "1" else f"{n} capsules per day"
        _add(out, product, "daily_dose", label, None, meta, text, m, offset)

    # vegan status ------------------------------------------------------------
    veg = _vegan_value(text)
    if veg:
        value, m = veg
        _add(out, product, "vegan", value, None, meta, text, m, offset)

    m = re.search(r"suitable for vegetarians:\s*(yes|no)", low)
    if m:
        _add(out, product, "vegetarian", m.group(1).capitalize(), None, meta, text, m, offset)

    # nutrient amounts (unit-aware) ------------------------------------------
    # Gap is [^\n]*? (not [^.\n]*?) so it crosses the OCR dot-leaders in the
    # datasheet, e.g. "Vitam1n B12 (Methylcobalam1n) .......... 25 ug". The
    # trailing unit anchor still prevents grabbing a stray number like "1000%".
    _nutrient(out, product, meta, text, offset, "b12",
              r"(?:vitamin\s*b\s*12|vitam1n\s*b12|methylcobalam1?n|cyanocobalamin)[^\n]*?(\d+(?:[.,]\d+)?)\s*(µg|ug|mcg|mg)")
    _nutrient(out, product, meta, text, offset, "dha",
              r"(?:omega-?3\s*)?dha[^\n]*?(\d+(?:[.,]\d+)?)\s*(mg)")
    # blog phrases the amount the other way round: "around 320 mg DHA"
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*mg\b[^\n]{0,15}?dha", text, re.I):
        _add(out, product, "dha", m.group(1).replace(",", "."), "mg", meta, text, m, offset)
    _nutrient(out, product, meta, text, offset, "folate",
              r"(?:folate|folat|folic acid)[^\n]*?(\d+(?:[.,]\d+)?)\s*(µg|ug|mcg|mg)")
    _nutrient(out, product, meta, text, offset, "vitamin_d",
              r"vitamin\s*d3?[^\n]*?(\d+(?:[.,]\d+)?)\s*(µg|ug|mcg|iu)")

    # price + market ----------------------------------------------------------
    for m in re.finditer(r"£\s*(\d+(?:[.,]\d+)?)", text):
        _add(out, product, "price", f"£{m.group(1)}", None, meta, text, m, offset, market="UK")
    for m in re.finditer(r"(?:€|EUR)\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*€", text):
        amt = m.group(1) or m.group(2)
        _add(out, product, "price", f"€{amt}", None, meta, text, m, offset, market="EU")
    for m in re.finditer(r"\$\s*(\d+(?:[.,]\d+)?)", text):
        _add(out, product, "price", f"${m.group(1)}", None, meta, text, m, offset, market="US")
    for m in re.finditer(r"(not published|currently unavailable|could not find an official[^.\n]*price)", low):
        _add(out, product, "price", "Not published / unavailable", None, meta, text, m, offset,
             market="EU/UK", conf=meta.authority)

    # marketing / health claims (verbatim, for the compliance tool) -----------
    for m in re.finditer(r"[^.\n]*\bimmune[^.\n]*", text, re.I):
        _add(out, product, "claim_immune", m.group(0).strip(), None, meta, text, m, offset)
    for m in re.finditer(r"[^.\n]*(?:energy metabolism|energy-yielding|energiestoffwechsel|energy release)[^.\n]*", text, re.I):
        _add(out, product, "claim_energy", m.group(0).strip(), None, meta, text, m, offset)


def _nutrient(out, product, meta, text, offset, attr, pattern):
    for m in re.finditer(pattern, text, re.I):
        value = m.group(1).replace(",", ".")
        _add(out, product, attr, value, _norm_unit(m.group(2)), meta, text, m, offset)


def _vegan_value(text: str):
    m = re.search(r"suitable for vegans:\s*(yes|no)", text, re.I)
    if m:
        return m.group(1).capitalize(), m
    m = re.search(r"not suitable for vegans[^.\n]*", text, re.I)
    if m:
        return "No", m
    m = re.search(r"\bgelatin[e]?\b", text, re.I)
    if m:
        return "No", m
    m = re.search(r"\bvegan\b", text, re.I)
    if m:
        return "Yes", m
    return None


def extract_all(metas: list[DocMeta], full_texts: dict[str, str]) -> list[Extraction]:
    out: list[Extraction] = []
    for meta in metas:
        if meta.origin == "regulatory-reference":
            continue
        text = full_texts[meta.id]
        for product, seg_text, offset in _segments(meta, text):
            _extract_segment(product, meta, seg_text, offset, out)
    return _dedupe(out)


def _dedupe(items: list[Extraction]) -> list[Extraction]:
    seen: dict[tuple, Extraction] = {}
    for it in items:
        key = (it.product, it.attribute, it.value, it.doc_id, it.market)
        if key not in seen:
            seen[key] = it
    return list(seen.values())
