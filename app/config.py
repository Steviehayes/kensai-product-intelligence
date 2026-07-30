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

# --- Chat provider ---------------------------------------------------------
# Two zero-cost options; whichever key is set wins (Groq first). Groq needs no
# billing and is the simplest to switch on; Gemini also does embeddings.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Retrieval -------------------------------------------------------------
CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "600"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "6"))

# --- Server ----------------------------------------------------------------
PORT = int(os.getenv("PORT", "7860"))  # 7860 is the Hugging Face Spaces default

# --- Optional access gate --------------------------------------------------
# If both are set, the whole app requires HTTP Basic Auth. Left unset for local
# dev so the app stays open with zero config.
APP_USER = os.getenv("APP_USER", "").strip()
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()


def auth_enabled() -> bool:
    return bool(APP_USER and APP_PASSWORD)


def google_enabled() -> bool:
    """Google key present → Gemini embeddings + Gemini chat are available."""
    return bool(GOOGLE_API_KEY)
