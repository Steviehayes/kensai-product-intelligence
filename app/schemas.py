"""Pydantic models shared across the API and the agent.

The `Citation` is the backbone of the whole app: nothing is asserted without one.
Every table cell, every chat answer, and every flag carries the exact source
snippet it came from.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

Confidence = Literal["high", "medium", "low"]


class Citation(BaseModel):
    doc_id: str
    title: str
    url: Optional[str] = None
    snippet: str  # the exact text the value was read from


class IntelligenceCell(BaseModel):
    """One row of the structured intelligence table."""

    product: str
    attribute: str
    value: str
    unit: Optional[str] = None
    confidence: Confidence
    flag: Optional[str] = None  # "conflict" | "compliance" | "missing" | None
    citations: list[Citation]


class Flag(BaseModel):
    kind: Literal["conflict", "missing_value", "non_compliant_claim", "data_quality"]
    product: Optional[str] = None
    attribute: Optional[str] = None
    summary: str
    detail: str
    citations: list[Citation]


class ChatAnswer(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    flags: list[Flag] = []
    used_llm: bool
    steps: list[str] = []  # human-readable trace of the tools the agent ran


class IngestResult(BaseModel):
    documents: int
    chunks: int
    products: int
    embeddings_backend: str
