"""FastAPI app exposing the single v1 endpoint: POST /chat.

Takes an English message (+ optional history) and an Anthropic key (header or
env), runs it through the router, and returns the shared output envelope. The
endpoint never crashes on a bad request — errors come back as ``type: "error"``
envelopes.
"""

from __future__ import annotations

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import get_settings, resolve_api_key
from .do_the_math.ir import Envelope
from .do_the_math.math_interpreter import MathInterpreter
from .do_the_math.providers.anthropic_adapter import AnthropicAdapter
from .do_the_math.router import Router, build_default_registry

settings = get_settings()
app = FastAPI(title="Do the Math", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict] | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.model}


@app.post("/chat", response_model=Envelope)
def chat(
    request: ChatRequest,
    x_anthropic_key: str | None = Header(default=None),
) -> Envelope:
    api_key = resolve_api_key(x_anthropic_key, settings)
    if not api_key:
        return Envelope.error(
            "No Anthropic API key provided. Enter your key to start graphing.",
            reason="missing_api_key",
        )

    adapter = AnthropicAdapter(api_key=api_key, model=settings.model)
    router = Router(MathInterpreter(adapter), build_default_registry())
    return router.handle(request.message, request.history)
