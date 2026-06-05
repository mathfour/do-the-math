"""The Graphing Agent — v1's only agent.

Thin orchestration over the shared math core:
interpreter output (raw IR) -> clarification check -> strict parse -> derive ->
render -> envelope. It owns no math itself; future agents reuse the same core.
"""

from __future__ import annotations

import pydantic

from ..clarification import REQUIRED, check_required
from ..errors import DerivationError, OutOfScopeError
from ..graph_renderer import render
from ..ir import Envelope, IntentWrapper
from ..math_engine import derive
from .base import Request

# Kinds this agent graphs. In v1 this is the whole IR vocabulary, so the agent
# also claims requests whose kind is missing/unknown — that's how it gets the
# chance to ask a clarifying question rather than dropping the request.
_GRAPHING_KINDS = frozenset(REQUIRED)


class GraphingAgent:
    name = "graphing"

    def can_handle(self, raw_intent: dict) -> bool:
        # v1 has a single agent, so it claims every request: known graphing
        # kinds it derives, and missing/unknown kinds it turns into a clarifying
        # question. Real classification (by kind) arrives with the second agent.
        return True

    def handles_kind(self, kind: str | None) -> bool:
        """Whether ``kind`` is a graphing kind this agent derives (vs. clarifies)."""
        return kind in _GRAPHING_KINDS

    def execute(self, request: Request) -> Envelope:
        raw = request.raw_intent

        # 1. Deterministic clarification: missing required field -> ask, don't guess.
        missing = check_required(raw)
        if missing is not None:
            return Envelope.clarification(missing.question, missing.field)

        # 2. Strict parse (rejects malformed/extra fields).
        try:
            intent = IntentWrapper(intent=raw).intent
        except pydantic.ValidationError:
            return Envelope.error(
                "I couldn't make sense of that request. Could you rephrase it?",
                reason="invalid_intent",
            )

        # 3. Derive + validate with SymPy (the source of mathematical truth).
        try:
            derived = derive(intent)
        except OutOfScopeError as exc:
            return Envelope.error(exc.message, reason=exc.reason)
        except DerivationError as exc:
            return Envelope.error(exc.message, reason=exc.reason)

        # 4. Render to a Plotly spec and return the graph envelope.
        figure = render(derived)
        explanation = f"Interpreted your request and derived {derived.equation}."
        return Envelope.graph(figure, derived.equation, ir=raw, explanation=explanation)
