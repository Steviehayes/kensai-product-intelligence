"""Runtime configuration.

Everything is driven by environment variables so the same image runs locally,
in Docker, and on a Hugging Face Space with no code changes. The only thing that
changes behaviour is whether GOOGLE_API_KEY is present:

  - key present  -> Gemini embeddings for retrieval + Gemini for chat synthesis
  - key absent   -> TF-IDF retrieval + extractive chat (deterministic layer still
                    fully works, so the app boots and answers with zero config)
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# --- LLM / embeddings provider (Google Gemini free tier) -------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")

# --- Retrieval -------------------------------------------------------------
CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "600"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "6"))

# --- Server ----------------------------------------------------------------
PORT = int(os.getenv("PORT", "7860"))  # 7860 is the Hugging Face Spaces default


def llm_enabled() -> bool:
    return bool(GOOGLE_API_KEY)
