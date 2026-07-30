"""Embeddings with a graceful fallback.

Primary path: Google `text-embedding-004` (free tier) — real semantic vectors.
Fallback path: TF-IDF (scikit-learn) so retrieval still works with no API key,
which keeps `docker compose up` a zero-config experience for a reviewer.

Both backends expose the same `embed_documents` / `embed_query` interface, so the
vector store neither knows nor cares which one is active.
"""

from __future__ import annotations

import numpy as np

from . import config


class GeminiEmbeddings:
    backend = "gemini:text-embedding-004"

    def __init__(self) -> None:
        import google.generativeai as genai

        genai.configure(api_key=config.GOOGLE_API_KEY)
        self._genai = genai

    def _embed(self, text: str, task: str) -> np.ndarray:
        resp = self._genai.embed_content(
            model=config.GEMINI_EMBED_MODEL, content=text, task_type=task
        )
        return np.asarray(resp["embedding"], dtype=np.float32)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._embed(t, "retrieval_document") for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed(text, "retrieval_query")


class TfidfEmbeddings:
    backend = "tfidf (offline fallback)"

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._fitted = False

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        matrix = self._vectorizer.fit_transform(texts)
        self._fitted = True
        return matrix.toarray().astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("embed_documents must be called before embed_query")
        return self._vectorizer.transform([text]).toarray().astype(np.float32)[0]


def build_embedder():
    if config.google_enabled():
        try:
            return GeminiEmbeddings()
        except Exception as exc:  # noqa: BLE001 - degrade rather than crash on boot
            print(f"[embeddings] Gemini unavailable ({exc}); using TF-IDF fallback")
    return TfidfEmbeddings()
