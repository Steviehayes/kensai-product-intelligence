"""A tiny in-memory vector store.

The corpus is 8 documents (~40 chunks), so a NumPy cosine-similarity search is
the honest, dependency-light choice — no external DB to stand up for a reviewer.
The interface (`add` / `search`) is deliberately the same shape you'd keep if you
swapped the internals for FAISS or pgvector at scale (see README, 10k-doc note).
"""

from __future__ import annotations

import numpy as np

from .ingest import Chunk


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class VectorStore:
    def __init__(self, embedder) -> None:
        self._embedder = embedder
        self._chunks: list[Chunk] = []
        self._vectors: np.ndarray | None = None

    @property
    def backend(self) -> str:
        return self._embedder.backend

    def add(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        vectors = self._embedder.embed_documents([c.text for c in chunks])
        self._vectors = _normalise(vectors)

    def search(self, query: str, top_k: int = 6, product: str | None = None):
        if self._vectors is None:
            raise RuntimeError("VectorStore is empty; call add() first")
        q = self._embedder.embed_query(query)
        q = q / (np.linalg.norm(q) or 1.0)
        scores = self._vectors @ q

        order = np.argsort(scores)[::-1]
        results = []
        for idx in order:
            chunk = self._chunks[idx]
            if product and product not in chunk.products:
                continue
            results.append((chunk, float(scores[idx])))
            if len(results) >= top_k:
                break
        return results
