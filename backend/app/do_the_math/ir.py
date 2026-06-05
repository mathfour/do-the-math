"""Math Intent (IR) schema and the output Envelope.

The IR is the structured intermediate representation between English and
validated math. The LLM produces it; SymPy (``math_engine``) is the source of
mathematical truth. The IR is a **discriminated union** over ``kind`` so new
object types slot in without touching consumers.

Numeric fields are typed ``Number = int | float | str`` on purpose: the engine
normalizes them to *exact* SymPy numbers (``Integer``/``Rational``/``sympify``),
which keeps derived equations readable and correct (``y = (x - 1)**2 + 2``,
not ``1.0*(x - 1.0)**2 + 2.0``). A string lets the model emit exact values like
``"1/3"`` or ``"sqrt(2)"``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# A numeric literal as it arrives in the IR (normalized to exact SymPy later).
Number = int | float | str
# (x, y) coordinate pair. Pydantic coerces a JSON list [1, 2] to a tuple.
Point = tuple[Number, Number]


class _IRModel(BaseModel):
    """Base for IR object models — reject hallucinated/extra fields."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Direct forms — coefficients given explicitly.
# --------------------------------------------------------------------------- #


class LinearDirect(_IRModel):
    kind: Literal["linear_direct"]
    slope: Number  # m
    intercept: Number  # b   ->  y = m*x + b


class QuadraticVertex(_IRModel):
    kind: Literal["quadratic_vertex"]
    a: Number  # leading coefficient
    h: Number  # vertex x
    k: Number  # vertex y   ->  y = a*(x - h)**2 + k


class QuadraticStandard(_IRModel):
    kind: Literal["quadratic_standard"]
    a: Number
    b: Number
    c: Number  # y = a*x**2 + b*x + c


class PolynomialDirect(_IRModel):
    kind: Literal["polynomial"]
    # Coefficients HIGHEST degree first: [a_n, ..., a_1, a_0].
    coefficients: list[Number] = Field(min_length=1)


class TrigDirect(_IRModel):
    kind: Literal["trig"]
    func: Literal["sin", "cos", "tan"]
    amplitude: Number = 1  # A
    frequency: Number = 1  # B
    phase: Number = 0  # C
    vertical_shift: Number = 0  # D   ->  y = A*func(B*x - C) + D


class ExponentialDirect(_IRModel):
    kind: Literal["exponential"]
    base: Number = "e"  # "e" or a positive number != 1
    coefficient: Number = 1  # a
    rate: Number = 1  # b
    vertical_shift: Number = 0  # d   ->  y = a*base**(b*x) + d


class LogarithmicDirect(_IRModel):
    kind: Literal["logarithmic"]
    base: Number = "e"  # "e", "10", or a positive number != 1
    coefficient: Number = 1  # a
    inner_coeff: Number = 1  # b
    h_shift: Number = 0  # h
    vertical_shift: Number = 0  # d   ->  y = a*log_base(b*(x - h)) + d


# --------------------------------------------------------------------------- #
# Geometric forms — described by points/vertex; genuinely derived by SymPy.
# --------------------------------------------------------------------------- #


class LineTwoPoints(_IRModel):
    kind: Literal["line_two_points"]
    point1: Point
    point2: Point


class LinePointSlope(_IRModel):
    kind: Literal["line_point_slope"]
    point: Point
    slope: Number


class ParabolaVertexDirection(_IRModel):
    kind: Literal["parabola_vertex_direction"]
    vertex: Point
    direction: Literal["up", "down"]
    a_magnitude: Number | None = None  # optional |a|, default 1


class ParabolaVertexPoint(_IRModel):
    kind: Literal["parabola_vertex_point"]
    vertex: Point
    point: Point  # a second point on the curve (!= vertex)


class ParabolaThreePoints(_IRModel):
    kind: Literal["parabola_three_points"]
    points: list[Point] = Field(min_length=3, max_length=3)


# --------------------------------------------------------------------------- #
# Out-of-scope — a first-class, deterministic way to decline.
# --------------------------------------------------------------------------- #


class Unsupported(_IRModel):
    kind: Literal["unsupported"]
    reason: Literal[
        "implicit",
        "parametric",
        "polar",
        "piecewise",
        "inequality",
        "not_a_function",
        "unknown",
    ]
    detail: str = ""


class HelpRequest(_IRModel):
    """The person is asking what the tool can do, not to graph something."""

    kind: Literal["help"]


# --------------------------------------------------------------------------- #
# The union.
# --------------------------------------------------------------------------- #

MathIntent = Annotated[
    LinearDirect
    | QuadraticVertex
    | QuadraticStandard
    | PolynomialDirect
    | TrigDirect
    | ExponentialDirect
    | LogarithmicDirect
    | LineTwoPoints
    | LinePointSlope
    | ParabolaVertexDirection
    | ParabolaVertexPoint
    | ParabolaThreePoints
    | Unsupported
    | HelpRequest,
    Field(discriminator="kind"),
]


class IntentWrapper(BaseModel):
    """Wrapper the LLM tool-call returns; also the source of the tool schema."""

    intent: MathIntent


# --------------------------------------------------------------------------- #
# Output envelope — every agent returns this shape.
# --------------------------------------------------------------------------- #

EnvelopeType = Literal["graph", "solution", "proof", "clarification", "error", "help"]


class Envelope(BaseModel):
    """Uniform agent output. ``payload`` shape depends on ``type``.

    - ``graph``: ``{"figure": <plotly spec>, "equation": str, "ir": {...}}``
    - ``clarification``: ``{"question": str, "field": str}``
    - ``error``: ``{"message": str, "reason": str}``
    - ``help``: ``{}`` — the UI renders the static capabilities answer.
    - ``solution`` / ``proof``: reserved for future agents.
    """

    type: EnvelopeType
    payload: dict
    explanation: str

    @classmethod
    def graph(cls, figure: dict, equation: str, ir: dict, explanation: str) -> Envelope:
        return cls(
            type="graph",
            payload={"figure": figure, "equation": equation, "ir": ir},
            explanation=explanation,
        )

    @classmethod
    def clarification(cls, question: str, field: str) -> Envelope:
        return cls(
            type="clarification",
            payload={"question": question, "field": field},
            explanation=question,
        )

    @classmethod
    def error(cls, message: str, reason: str = "error") -> Envelope:
        return cls(
            type="error",
            payload={"message": message, "reason": reason},
            explanation=message,
        )

    @classmethod
    def help(cls, explanation: str) -> Envelope:
        return cls(type="help", payload={}, explanation=explanation)
