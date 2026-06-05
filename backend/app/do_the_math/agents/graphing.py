"""The Graphing Agent — v1's only agent.

Thin orchestration over the shared math core:
interpreter output (raw IR) -> clarification check -> strict parse -> derive ->
render -> envelope. It owns no math itself; future agents reuse the same core.
"""

from __future__ import annotations

import logging
import os

import pydantic

from ..clarification import REQUIRED, check_required
from ..describe import friendly_summary, summary_facts
from ..errors import DerivationError, OutOfScopeError
from ..graph_renderer import render
from ..ir import Envelope, HelpRequest, IntentWrapper
from ..math_engine import derive
from .base import Request

logger = logging.getLogger(__name__)

# Per-graph LLM phrasing makes each result line fresh wording, but costs a second
# Anthropic call per graph. It's OFF by default to conserve API tokens during
# testing; the code path below is fully preserved. Re-enable by flipping this to
# True, or by setting DTM_LLM_SUMMARIES=1 in the environment.
LLM_SUMMARIES_ENABLED = os.getenv("DTM_LLM_SUMMARIES", "0").lower() in ("1", "true", "yes")

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

        # 2b. A help question ("what can I graph?") gets a friendly answer, not a
        # graph. The capabilities text is rendered by the UI (static, no model).
        if isinstance(intent, HelpRequest):
            return Envelope.help("Here's what I can graph right now.")

        # 3. Derive + validate with SymPy (the source of mathematical truth).
        try:
            derived = derive(intent)
        except OutOfScopeError as exc:
            return Envelope.error(exc.message, reason=exc.reason)
        except DerivationError as exc:
            return Envelope.error(exc.message, reason=exc.reason)

        # 4. Render to a Plotly spec and return the graph envelope.
        figure = render(derived)
        explanation = _summarize(request.provider, intent, derived)
        return Envelope.graph(figure, derived.equation, ir=raw, explanation=explanation)


def _summarize(provider, intent, derived) -> str:
    """Ask the model to phrase the result for variety; fall back to a written
    line if phrasing is disabled, there's no provider, or the call fails. The
    facts are SymPy-verified, so the model only rephrases — it never owns the math."""
    if LLM_SUMMARIES_ENABLED and provider is not None:
        try:
            text = provider.write_summary(summary_facts(intent, derived))
            if text and text.strip():
                return text.strip()
        except Exception:
            logger.warning("Summary phrasing failed; using the written line.", exc_info=True)
    return friendly_summary(intent, derived)
