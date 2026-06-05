"""Anthropic provider adapter — English -> raw Math Intent dict.

Uses Anthropic tool-use: a single tool whose ``input_schema`` is the IR union's
JSON schema, with ``tool_choice`` forcing the model to call it. This makes Claude
emit a structurally-valid-shaped IR (``kind`` + fields) rather than free text we
have to parse. SymPy — not this adapter — remains the source of mathematical
truth; the adapter only does language understanding.

Model id (``claude-sonnet-4-6``) is confirmed current Sonnet 4.6 and lives in
config so it's swappable.
"""

from __future__ import annotations

from functools import lru_cache

import anthropic

from ..ir import IntentWrapper

_TOOL_NAME = "submit_math_intent"

_SYSTEM_PROMPT = """\
You translate a person's plain-English description of a 2D graph into a structured \
Math Intent by calling the `submit_math_intent` tool. You do not do the math — a \
deterministic engine derives the equation from your intent. Your only job is to \
capture *what the person asked for*.

Rules:
- Always call the tool exactly once. Choose the single `kind` that best matches.
- Prefer the geometric kinds when the person speaks geometrically (a parabola by \
its vertex and direction, a line through two points, a parabola through a vertex \
plus another point). Use the direct kinds when they give coefficients outright.
- Only fill in a field if the person actually specified it. If a required value is \
missing (e.g. they said "graph a parabola" but gave no vertex), OMIT that field — \
do not invent or assume a value. A separate step will ask the person for it.
- If the request is out of scope for 2D y = f(x) graphing — implicit equations \
(like x^2 + y^2 = 25), parametric curves, polar graphs, piecewise functions, or \
inequalities — use kind "unsupported" with the matching reason.
"""


@lru_cache(maxsize=1)
def _tool_schema() -> dict:
    """The tool's input schema = the IR wrapper's JSON schema (built once)."""
    return {
        "name": _TOOL_NAME,
        "description": "Submit the structured Math Intent for the requested graph.",
        "input_schema": IntentWrapper.model_json_schema(),
    }


class AnthropicAdapter:
    """Maps English -> raw IR dict via Anthropic tool-use."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str, *, max_tokens: int = 1024):
        if not api_key:
            raise ValueError("An Anthropic API key is required.")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete_intent(self, message: str, history: list[dict] | None = None) -> dict:
        messages = list(history or []) + [{"role": "user", "content": message}]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=_SYSTEM_PROMPT,
            tools=[_tool_schema()],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=messages,
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == _TOOL_NAME:
                payload = dict(block.input)  # already parsed by the SDK
                # The tool wraps the intent; tolerate a flat intent too.
                intent = payload.get("intent", payload)
                return dict(intent)
        raise RuntimeError("Anthropic did not return a Math Intent tool call.")
