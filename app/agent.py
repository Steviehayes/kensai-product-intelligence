"""The agent: ingest pipeline + multi-step chat.

Ingest pipeline (runs once, on startup):
    load+chunk -> embed -> extract structured data -> check claim compliance
    -> reconcile conflicts/missing -> cache table + flags.

Chat (per question) works in steps, not one prompt:
    1. detect which product(s)/attribute the question is about
    2. retrieve the top-k relevant snippets (never the whole corpus)
    3. gather the reconciled structured facts + flags for that product
    4. synthesise a cited answer (Gemini) — or an extractive answer if no key
Nothing is asserted without a citation; missing facts return "not found".
"""

from __future__ import annotations

from . import config
from .compliance import assess_claims
from .conflicts import analyse
from .embeddings import build_embedder
from .extract import extract_all
from .ingest import load_documents, full_text
from .llm import build_chat
from .schemas import ChatAnswer, Citation, Flag, IngestResult, IntelligenceCell
from .vectorstore import VectorStore

PRODUCT_HINTS = {
    "ritual": ["ritual"],
    "wellwoman": ["wellwoman", "well woman", "vitabiotics"],
    "moleqlar": ["moleqlar", "b komplex", "b-komplex", "b complex", "vitamin b komplex"],
}
ATTRIBUTE_HINTS = {
    "Suitable for vegans": ["vegan"],
    "Suitable for vegetarians": ["vegetarian"],
    "Vitamin B12 per capsule": ["b12", "b 12"],
    "Omega-3 DHA": ["dha", "omega"],
    "Recommended daily dose": ["dose", "daily", "per day", "how many", "take", "serving"],
    "Pack size": ["pack", "supply", "how many cap"],
    "Price": ["price", "cost", "rrp", "retail", "cheap", "expensive"],
    "Health claim compliance": ["immune", "boost", "compliant", "compliance", "claim", "legal", "energy metabolism"],
}


class KnowledgeBase:
    def __init__(self) -> None:
        self.table: list[IntelligenceCell] = []
        self.flags: list[Flag] = []
        self._store: VectorStore | None = None
        self._chat = build_chat()
        self._embed_backend = "not built"

    # -- ingest --------------------------------------------------------------
    def build(self) -> IngestResult:
        metas, chunks, catalogue = load_documents()
        embedder = build_embedder()
        self._store = VectorStore(embedder)
        self._store.add(chunks)
        self._embed_backend = self._store.backend

        full_texts = {m.id: full_text(m.id, metas) for m in metas}
        extractions = extract_all(metas, full_texts)
        reference_text = full_texts["08_health_claims_reference"]
        verdicts = assess_claims(extractions, reference_text)
        self.table, self.flags = analyse(extractions, verdicts, metas)

        return IngestResult(
            documents=len(metas), chunks=len(chunks),
            products=len(catalogue["products"]), embeddings_backend=self._store.backend,
        )

    @property
    def embeddings_backend(self) -> str:
        return self._embed_backend

    @property
    def llm_enabled(self) -> bool:
        return self._chat is not None

    # -- chat ----------------------------------------------------------------
    def answer(self, question: str) -> ChatAnswer:
        if self._store is None:
            raise RuntimeError("KnowledgeBase not built")
        steps: list[str] = []
        q = question.lower()

        products = [p for p, kws in PRODUCT_HINTS.items() if any(k in q for k in kws)]
        attributes = [a for a, kws in ATTRIBUTE_HINTS.items() if any(k in q for k in kws)]
        steps.append(f"detect: products={products or 'any'}, attributes={attributes or 'any'}")

        product_filter = products[0] if len(products) == 1 else None
        hits = self._store.search(question, top_k=config.RETRIEVAL_TOP_K, product=product_filter)
        steps.append(f"retrieve: {len(hits)} snippets (product filter={product_filter or 'none'})")

        cells = self._relevant_cells(products, attributes)
        flags = self._relevant_flags(products, attributes)
        steps.append(f"reconcile: {len(cells)} structured facts, {len(flags)} flags in scope")

        if self._chat is not None:
            answer_text = self._synthesise(question, hits, cells)
            steps.append("synthesise: Gemini grounded on evidence")
            used_llm = True
        else:
            answer_text = self._extractive(attributes, cells, hits)
            steps.append("synthesise: extractive (no LLM key set)")
            used_llm = False

        citations = self._citations(cells, hits)
        return ChatAnswer(question=question, answer=answer_text, citations=citations,
                          flags=flags, used_llm=used_llm, steps=steps)

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _matches(cell_attr: str, attributes: list[str]) -> bool:
        return any(cell_attr.startswith(a) or a.startswith(cell_attr) for a in attributes)

    def _relevant_cells(self, products, attributes) -> list[IntelligenceCell]:
        scope = products or ["ritual", "wellwoman", "moleqlar"]
        cells = [c for c in self.table if c.product in scope]
        if attributes:
            cells = [c for c in cells if self._matches(c.attribute, attributes)] or cells
        return cells

    def _relevant_flags(self, products, attributes) -> list[Flag]:
        if not products:
            return []
        out = []
        for f in self.flags:
            if f.product not in products:
                continue
            if attributes and f.attribute and not self._matches(f.attribute, attributes):
                continue
            out.append(f)
        return out

    def _synthesise(self, question, hits, cells) -> str:
        evidence = "\n".join(f"[{c.doc_id}] {c.text}" for c, _ in hits)
        facts = "\n".join(
            f"- {c.product} {c.attribute}: {c.value}{(' ' + c.unit) if c.unit else ''}"
            f"{' [FLAG: ' + c.flag + ']' if c.flag else ''} (sources: "
            f"{', '.join(sorted({ci.doc_id for ci in c.citations})) or 'none'})"
            for c in cells
        )
        prompt = (
            f"QUESTION: {question}\n\n"
            f"RECONCILED STRUCTURED FACTS (already cross-checked across sources):\n{facts or 'none'}\n\n"
            f"EVIDENCE SNIPPETS (verbatim from sources):\n{evidence or 'none'}\n\n"
            "Answer the question using only the above. Quote units exactly, surface any conflict, "
            "and cite document ids inline. If it is not present, say 'Not found in the sources.'"
        )
        return self._chat.generate(prompt) or self._extractive([], cells, hits)

    @staticmethod
    def _extractive(attributes, cells, hits) -> str:
        focus = [c for c in cells if not attributes or KnowledgeBase._matches(c.attribute, attributes)]
        if attributes and focus:
            lines = []
            for c in focus:
                val = f"{c.value}{(' ' + c.unit) if c.unit else ''}"
                note = ""
                if c.flag == "conflict":
                    note = " — sources conflict (see flags/citations); value shown is from the highest-authority source."
                elif c.flag == "missing":
                    note = " — not stated in any source."
                elif c.flag == "compliance":
                    note = " — see compliance flag."
                lines.append(f"{c.product}: {c.attribute} = {val}{note}")
            return "\n".join(lines)
        if hits:
            top = "\n".join(f"[{c.doc_id}] {c.text}" for c, _ in hits[:3])
            return ("No single reconciled fact matched; most relevant source snippets:\n" + top +
                    "\n\n(Set GOOGLE_API_KEY to enable full natural-language synthesis.)")
        return "Not found in the sources."

    @staticmethod
    def _citations(cells, hits) -> list[Citation]:
        # Prefer the reconciled cell citations — those are the exact sources the
        # value was read from. Only fall back to raw retrieved snippets when no
        # structured fact matched, so we never cite a tangential document.
        seen: set[tuple] = set()
        out: list[Citation] = []
        for c in cells:
            for ci in c.citations:
                key = (ci.doc_id, ci.snippet)
                if key not in seen:
                    seen.add(key)
                    out.append(ci)
        if not out:
            for chunk, _ in hits[:3]:
                out.append(Citation(doc_id=chunk.doc_id, title=chunk.title, url=chunk.url, snippet=chunk.text))
        return out[:8]
