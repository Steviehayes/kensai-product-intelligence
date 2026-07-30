"""FastAPI surface for the product-intelligence agent.

Endpoints:
    GET  /health         service + backend status
    POST /ingest         (re)build the knowledge base from data/
    POST /query          ask a question -> cited answer + in-scope flags
    GET  /intelligence   the structured table (product·attribute·value·source·confidence·flag)
    GET  /flags          the full flags report (conflicts, missing values, non-compliant claims)
    GET  /examples       the 6 sample questions (prompts only, not answers)
The same process serves the static frontend, so one container is the whole app.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .agent import KnowledgeBase
from .auth import BasicAuthMiddleware

kb = KnowledgeBase()

EXAMPLES = [
    "What is the recommended daily dose and pack size of Vitabiotics Wellwoman Original, and the original source?",
    "Is Ritual Essential for Women vegan? Cite your source.",
    "How much Vitamin B12 is in one capsule of MoleQlar Vitamin B Komplex?",
    "Is Vitabiotics Wellwoman Original suitable for vegans?",
    "The UK listing for Ritual claims it 'boosts your immune system.' Is that compliant for the EU/UK market? Why?",
    "What is the official EU/UK retail price of Ritual Essential for Women?",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    result = kb.build()
    print(f"[ingest] {result.documents} docs, {result.chunks} chunks, "
          f"embeddings={result.embeddings_backend}, llm={'on' if kb.llm_enabled else 'off'}")
    yield


app = FastAPI(title="Kensai Product Intelligence Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(BasicAuthMiddleware)  # no-op unless APP_USER/APP_PASSWORD are set


class Query(BaseModel):
    question: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_enabled": kb.llm_enabled,
        "embeddings_backend": kb.embeddings_backend,
        "intelligence_rows": len(kb.table),
        "flags": len(kb.flags),
    }


@app.post("/ingest")
def ingest():
    return kb.build()


@app.post("/query")
def query(q: Query):
    return kb.answer(q.question)


@app.get("/intelligence")
def intelligence():
    return kb.table


@app.get("/flags")
def flags():
    return kb.flags


@app.get("/examples")
def examples():
    return EXAMPLES


# --- static frontend (served last so it doesn't shadow the API routes) ------
@app.get("/")
def index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")
