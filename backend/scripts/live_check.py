"""Live end-to-end check against the real Anthropic API.

Reads ANTHROPIC_API_KEY (+ optional ANTHROPIC_MODEL) from backend/.env and runs
a few real requests through the full slice: English -> Anthropic -> IR -> SymPy
-> Plotly envelope. This is NOT a unit test (it costs tokens); run it manually:

    cd backend && uv run python scripts/live_check.py
"""

from __future__ import annotations

from app.config import get_settings
from app.do_the_math.math_interpreter import MathInterpreter
from app.do_the_math.providers.anthropic_adapter import AnthropicAdapter
from app.do_the_math.router import Router, build_default_registry

PROMPTS = [
    "I need a parabola with the vertex at (1, 2), opening upward.",
    "draw the line through (0, 0) and (2, 4)",
    "graph a parabola",  # underspecified -> expect clarification
    "graph the circle x^2 + y^2 = 25",  # out of scope -> expect error
    "plot sine wave with amplitude 3",
]


def main() -> None:
    settings = get_settings()
    if not settings.env_api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY in backend/.env first.")

    adapter = AnthropicAdapter(api_key=settings.env_api_key, model=settings.model)
    router = Router(MathInterpreter(adapter), build_default_registry())

    print(f"model: {settings.model}\n")
    for prompt in PROMPTS:
        env = router.handle(prompt)
        print(f"> {prompt}")
        print(f"  type={env.type}")
        if env.type == "graph":
            print(f"  ir={env.payload['ir']}")
            print(f"  equation={env.payload['equation']}")
        elif env.type == "clarification":
            print(f"  question={env.payload['question']}")
        elif env.type == "error":
            print(f"  reason={env.payload['reason']}  message={env.payload['message']}")
        print()


if __name__ == "__main__":
    main()
