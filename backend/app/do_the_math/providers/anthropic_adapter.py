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

import json
import logging
from functools import lru_cache

import anthropic

from ..ir import IntentWrapper

logger = logging.getLogger(__name__)

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
- For polynomials, HONOR any stated degree or order: "fourth-order", "degree 4", \
or "quartic" means the `coefficients` list has exactly degree+1 numbers (so 5 for \
a quartic), highest power first, with a nonzero leading coefficient. When the \
person wants "lots of turning points", "hills and valleys", or a "wiggly" curve, \
choose coefficients that genuinely turn many times — the reliable way is to pick a \
polynomial with several DISTINCT real roots (a degree-n polynomial with n distinct \
real roots turns n-1 times) and expand it to coefficients. A degree-n polynomial \
can turn at most n-1 times, so to maximize hills and valleys use that many distinct \
roots. If they say "not all even" or "asymmetric", include both even and odd powers \
so the curve isn't symmetric. Double-check your coefficients give the degree asked for.
- If the request is out of scope for 2D y = f(x) graphing — implicit equations \
(like x^2 + y^2 = 25), parametric curves, polar graphs, piecewise functions, or \
inequalities — use kind "unsupported" with the matching reason.
- If the person is asking what this tool can do, what they can graph, for examples, \
or for help (a question about Do the Math itself, not a request to graph a specific \
thing — e.g. "what can I graph?", "what can you do?", "help") — use kind "help".
"""


_SUMMARY_SYSTEM = """\
You are the warm, playful voice of "Do the Math", a graphing app. You'll be given \
verified facts about a graph the app just produced. Write ONE short, friendly, \
casual sentence presenting it to the person — a little personality is great, and \
vary your wording every time.

Hard rules:
- Include the equation EXACTLY as given, character for character (keep its symbols).
- State only the facts provided. Never invent, add, or change a number.
- One sentence. No preamble, no markdown, no surrounding quotes.
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
                return _extract_intent(block.input)
        raise RuntimeError("Anthropic did not return a Math Intent tool call.")

    def write_summary(self, facts: dict) -> str:
        lines = [f"shape: {facts.get('shape', '')}", f"equation: {facts.get('equation', '')}"]
        if facts.get("details"):
            lines.append(f"facts: {facts['details']}")
        response = self._client.messages.create(
            model=self._model,
            max_tokens=200,
            system=_SUMMARY_SYSTEM,
            messages=[{"role": "user", "content": "\n".join(lines)}],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise RuntimeError("Anthropic returned an empty summary.")
        return text


def _extract_intent(tool_input) -> dict:
    """Pull the raw IR dict out of the tool-call input, tolerating shapes.

    The tool schema wraps the intent as ``{"intent": {...}}``, but the model
    sometimes returns the intent flat (``{"kind": ...}``) or serializes the
    object to a JSON string. Recover those; anything else is malformed.
    """
    if not isinstance(tool_input, dict):
        raise RuntimeError(f"Tool input was not an object: {type(tool_input).__name__}.")

    intent = tool_input.get("intent", tool_input)
    if isinstance(intent, str):
        try:
            intent = json.loads(intent)
        except json.JSONDecodeError:
            pass
    if not isinstance(intent, dict):
        logger.warning("Malformed Math Intent from model: %r", tool_input)
        raise RuntimeError(
            f"Math Intent was malformed (got {type(intent).__name__}, not an object)."
        )
    return intent
