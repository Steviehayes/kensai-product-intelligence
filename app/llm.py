"""Thin Gemini chat wrapper.

Only one job: turn a grounded prompt into text. All grounding, retrieval and
citation logic lives in the agent — the LLM is used purely to phrase an answer
from evidence it is handed, never as a knowledge source. If no key is set,
`generate` returns None and the agent falls back to an extractive answer.
"""

from __future__ import annotations

from . import config

_SYSTEM = """You are a product-intelligence analyst for EU/UK supplements.
Answer ONLY from the EVIDENCE snippets provided. Rules:
- If the evidence does not contain the answer, say exactly: "Not found in the sources."
- Never use outside knowledge or guess a number.
- Get units exactly right (µg vs mg vs IU) and quote them as written.
- If sources disagree, say so explicitly and give both values with their sources.
- Be concise and factual. Cite the document id (e.g. [03_wellwoman_official]) inline.
"""


class GeminiChat:
    backend = "gemini"

    def __init__(self) -> None:
        import google.generativeai as genai

        genai.configure(api_key=config.GOOGLE_API_KEY)
        self._model = genai.GenerativeModel(
            config.GEMINI_CHAT_MODEL, system_instruction=_SYSTEM
        )

    def generate(self, prompt: str) -> str | None:
        try:
            resp = self._model.generate_content(prompt)
            return (resp.text or "").strip()
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] gemini generation failed: {exc}")
            return None


class GroqChat:
    """Groq's OpenAI-compatible endpoint. Free tier, no billing, no extra deps."""

    backend = "groq"

    def __init__(self) -> None:
        self._key = config.GROQ_API_KEY
        self._model = config.GROQ_MODEL

    def generate(self, prompt: str) -> str | None:
        import json
        import ssl
        import urllib.request

        import certifi

        body = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions", data=body,
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
                # Groq's edge rejects the default Python-urllib agent with a 403.
                "User-Agent": "kensai-product-intelligence/1.0",
            },
        )
        ctx = ssl.create_default_context(cafile=certifi.where())
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                data = json.load(resp)
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] groq generation failed: {exc}")
            return None


def build_chat():
    """Whichever key is set wins — Groq first (simplest, no billing), then Gemini."""
    if config.GROQ_API_KEY:
        try:
            return GroqChat()
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] Groq unavailable ({exc})")
    if config.GOOGLE_API_KEY:
        try:
            return GeminiChat()
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] Gemini unavailable ({exc})")
    return None
