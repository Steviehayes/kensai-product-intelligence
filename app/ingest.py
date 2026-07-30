"""Document loading + chunking.

Loads the 8 source documents, normalises each format (HTML is stripped to text),
and splits them into small overlapping-by-paragraph chunks with source metadata
attached. Keeping chunks small and provenance-tagged is what lets retrieval hand
the LLM a handful of snippets rather than the whole corpus.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .config import DATA_DIR, CHUNK_MAX_CHARS


@dataclass
class DocMeta:
    id: str
    file: str
    title: str
    products: list[str]
    market: str
    format: str
    origin: str
    authority: str
    url: str | None


@dataclass
class Chunk:
    doc_id: str
    title: str
    url: str | None
    products: list[str]
    text: str
    order: int = 0
    meta: dict = field(default_factory=dict)


def _read_raw(fmt: str, path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if fmt == "html":
        soup = BeautifulSoup(raw, "html.parser")
        # keep label/value structure readable: "Pack size: 30 Capsules"
        for li in soup.find_all("li"):
            spans = li.find_all("span")
            if spans:
                li.string = " ".join(li.stripped_strings)
        return soup.get_text("\n")
    return raw


def _split(text: str, max_chars: int) -> list[str]:
    """Split on blank lines, then pack paragraphs up to max_chars.

    A single logical fact (e.g. a nutrient line) is never split mid-line, so a
    retrieved snippet is always a complete, quotable statement.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # long block: fall back to line-level packing
            for line in para.splitlines():
                line = line.strip()
                if not line:
                    continue
                if len(buf) + len(line) + 1 > max_chars and buf:
                    chunks.append(buf.strip())
                    buf = ""
                buf += line + "\n"
            continue
        if len(buf) + len(para) + 2 > max_chars and buf:
            chunks.append(buf.strip())
            buf = ""
        buf += para + "\n\n"
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def load_documents() -> tuple[list[DocMeta], list[Chunk], dict]:
    catalogue = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    metas: list[DocMeta] = []
    chunks: list[Chunk] = []

    for entry in catalogue["documents"]:
        meta = DocMeta(
            id=entry["id"],
            file=entry["file"],
            title=entry["title"],
            products=entry["products"],
            market=entry["market"],
            format=entry["format"],
            origin=entry["origin"],
            authority=entry["authority"],
            url=entry.get("url"),
        )
        metas.append(meta)
        text = _read_raw(meta.format, DATA_DIR / meta.file)
        for i, piece in enumerate(_split(text, CHUNK_MAX_CHARS)):
            chunks.append(
                Chunk(
                    doc_id=meta.id,
                    title=meta.title,
                    url=meta.url,
                    products=meta.products,
                    text=piece,
                    order=i,
                    meta={"authority": meta.authority, "origin": meta.origin, "market": meta.market},
                )
            )
    return metas, chunks, catalogue


def full_text(doc_id: str, metas: list[DocMeta]) -> str:
    meta = next(m for m in metas if m.id == doc_id)
    return _read_raw(meta.format, DATA_DIR / meta.file)
