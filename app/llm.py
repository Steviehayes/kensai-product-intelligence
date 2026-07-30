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
            print(f"[llm] generation failed: {exc}")
            return None


def build_chat() -> GeminiChat | None:
    if not config.llm_enabled():
        return None
    try:
        return GeminiChat()
    except Exception as exc:  # noqa: BLE001
        print(f"[llm] Gemini unavailable ({exc})")
        return None
