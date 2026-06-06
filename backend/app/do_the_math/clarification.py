"""Deterministic clarification check.

Underspecified requests must ask, not guess. The honest signal is whether the
IR's *required* fields are present — not an LLM confidence float. This runs on
the raw IR dict **before** strict Pydantic construction (which would otherwise
throw on missing required fields), and returns the first missing field as one
targeted question.
"""

from __future__ import annotations

from dataclasses import dataclass

# Required fields per IR kind. Optional/defaulted fields are intentionally
# absent here (e.g. trig amplitude, exponential base) — their defaults are fine.
REQUIRED: dict[str, list[str]] = {
    "linear_direct": ["slope", "intercept"],
    "quadratic_vertex": ["a", "h", "k"],
    "quadratic_standard": ["a", "b", "c"],
    "polynomial": ["coefficients"],
    "trig": ["func"],
    "exponential": [],
    "logarithmic": [],
    "line_two_points": ["point1", "point2"],
    "line_point_slope": ["point", "slope"],
    "parabola_vertex_direction": ["vertex", "direction"],
    "parabola_vertex_point": ["vertex", "point"],
    "parabola_three_points": ["points"],
    "unsupported": ["reason"],
    "help": [],
}

# Targeted question per (kind, field). Falls back to a generic prompt.
QUESTION: dict[tuple[str, str], str] = {
    ("linear_direct", "slope"): "What is the slope of the line?",
    ("linear_direct", "intercept"): "What is the y-intercept of the line?",
    ("quadratic_vertex", "a"): "What is the leading coefficient (how stretched is the parabola)?",
    ("quadratic_vertex", "h"): "What is the x-coordinate of the vertex?",
    ("quadratic_vertex", "k"): "What is the y-coordinate of the vertex?",
    ("quadratic_standard", "a"): "What is the coefficient of x²?",
    ("quadratic_standard", "b"): "What is the coefficient of x?",
    ("quadratic_standard", "c"): "What is the constant term?",
    ("polynomial", "coefficients"): "What are the polynomial's coefficients (highest power first)?",
    ("trig", "func"): "Which trig function — sin, cos, or tan?",
    ("line_two_points", "point1"): "What is the first point the line passes through? (e.g. (0, 1))",
    (
        "line_two_points",
        "point2",
    ): "What is the second point the line passes through? (e.g. (2, 5))",
    ("line_point_slope", "point"): "What point does the line pass through? (e.g. (1, 3))",
    ("line_point_slope", "slope"): "What is the slope of the line?",
    ("parabola_vertex_direction", "vertex"): "Where is the vertex of the parabola? (e.g. (1, 2))",
    ("parabola_vertex_direction", "direction"): "Does the parabola open upward or downward?",
    ("parabola_vertex_point", "vertex"): "Where is the vertex of the parabola? (e.g. (0, 0))",
    (
        "parabola_vertex_point",
        "point",
    ): "Give another point the parabola passes through. (e.g. (1, 3))",
    ("parabola_three_points", "points"): "Which three points should the parabola pass through?",
}


@dataclass(frozen=True)
class ClarificationNeeded:
    """A single targeted question for one missing required field."""

    field: str
    question: str


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, (list, str, dict)) and len(value) == 0)


def check_required(raw: dict) -> ClarificationNeeded | None:
    """Return the first missing-required-field clarification, or None if complete."""
    kind = raw.get("kind")
    # Guard `isinstance(str)` first: a non-string kind (e.g. a list) is both
    # invalid and unhashable, so `kind not in REQUIRED` would raise TypeError.
    if not isinstance(kind, str) or kind not in REQUIRED:
        return ClarificationNeeded(
            "kind", "What kind of function would you like to graph (e.g. a line or a parabola)?"
        )
    for field in REQUIRED[kind]:
        if _is_missing(raw.get(field)):
            question = QUESTION.get((kind, field), f"Please provide the {field}.")
            return ClarificationNeeded(field, question)
    return None
