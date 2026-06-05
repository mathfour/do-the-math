"""Human-friendly summaries of a derived function.

Produces the conversational line shown above each graph: a playful opener that
names the shape, plus one short, shape-specific note. The note's numbers come
from SymPy (the source of mathematical truth), and every note is computed
defensively — a tricky case degrades to just the opener, never an error.
"""

from __future__ import annotations

import sympy as sp

from .formatting import pretty_equation
from .ir import (
    ExponentialDirect,
    LogarithmicDirect,
    MathIntent,
    PolynomialDirect,
    TrigDirect,
)
from .math_engine import DerivedFunction, real_solutions, x

__all__ = ["friendly_summary", "summary_facts", "pretty_equation"]

_LINE_KINDS = {"linear_direct", "line_two_points", "line_point_slope"}
_PARABOLA_KINDS = {
    "quadratic_vertex",
    "quadratic_standard",
    "parabola_vertex_direction",
    "parabola_vertex_point",
    "parabola_three_points",
}
_TRIG_NOUN = {"sin": "sine wave", "cos": "cosine wave", "tan": "tangent curve"}


def friendly_summary(intent: MathIntent, derived: DerivedFunction) -> str:
    """The conversational explanation line for a graph result."""
    noun = _noun(intent, derived)
    opener = _opener(intent, noun, pretty_equation(derived.equation))
    try:
        note = _note(intent, derived)
    except Exception:  # a math note is a nicety — never let it break the reply
        note = ""
    return f"{opener} {note}".strip()


def summary_facts(intent: MathIntent, derived: DerivedFunction) -> dict:
    """SymPy-verified facts for the LLM to phrase (it must not change numbers)."""
    try:
        detail = _note(intent, derived)
    except Exception:
        detail = ""
    return {
        "shape": _noun(intent, derived),
        "equation": pretty_equation(derived.equation),
        "details": detail,
    }


# --------------------------------------------------------------------------- #
# Shape noun + playful opener.
# --------------------------------------------------------------------------- #


def _noun(intent: MathIntent, derived: DerivedFunction) -> str:
    if isinstance(intent, TrigDirect):
        return _TRIG_NOUN.get(intent.func, "trig curve")
    if isinstance(intent, ExponentialDirect):
        return "exponential curve"
    if isinstance(intent, LogarithmicDirect):
        return "logarithmic curve"
    if derived.kind in _LINE_KINDS:
        return "line"
    if derived.kind in _PARABOLA_KINDS:
        return "parabola"
    if isinstance(intent, PolynomialDirect):
        degree = _safe_degree(derived.expr)
        if degree == 1:
            return "line"
        if degree == 2:
            return "parabola"
        if degree == 3:
            return "cubic curve"
        if degree:
            return f"degree-{degree} curve"
    return "curve"


def _opener(intent: MathIntent, noun: str, equation: str) -> str:
    if isinstance(intent, TrigDirect):
        return f"Ooh, fun one! Here's your {noun}: {equation}."
    if noun == "parabola":
        return f"Nice — one parabola, coming right up: {equation}."
    if noun == "line":
        return f"Easy — here's your line: {equation}."
    return f"Here you go — your {noun}: {equation}."


# --------------------------------------------------------------------------- #
# Shape-specific notes (computed from the validated SymPy expression).
# --------------------------------------------------------------------------- #


def _note(intent: MathIntent, derived: DerivedFunction) -> str:
    expr = derived.expr
    if isinstance(intent, TrigDirect):
        return _trig_note(intent)
    if isinstance(intent, ExponentialDirect):
        return _exponential_note(intent)
    if isinstance(intent, LogarithmicDirect):
        return _log_note(derived)
    if derived.kind in _LINE_KINDS or _safe_degree(expr) == 1:
        return _line_note(expr)
    if derived.kind in _PARABOLA_KINDS or _safe_degree(expr) == 2:
        return _parabola_note(expr)
    if isinstance(intent, PolynomialDirect):
        return _polynomial_note(expr)
    return ""


def _line_note(expr: sp.Expr) -> str:
    expr = sp.expand(expr)
    slope = sp.simplify(expr.coeff(x, 1))
    intercept = sp.simplify(expr.subs(x, 0))
    if slope == 0:
        return f"It's flat — y stays at {_fmt(intercept)}."
    verb = "climbs" if slope > 0 else "drops"
    return (
        f"It {verb} {_fmt(sp.Abs(slope))} for every step right, "
        f"crossing the y-axis at {_fmt(intercept)}."
    )


def _parabola_note(expr: sp.Expr) -> str:
    expr = sp.expand(expr)  # vertex form (x - 1)**2 isn't a degree-2 coeff until expanded
    a = sp.simplify(expr.coeff(x, 2))
    b = sp.simplify(expr.coeff(x, 1))
    h = sp.simplify(-b / (2 * a))
    k = sp.simplify(expr.subs(x, h))
    opens = "upward" if a > 0 else "downward"
    return f"Its vertex sits at ({_fmt(h)}, {_fmt(k)}) and it opens {opens}."


def _polynomial_note(expr: sp.Expr) -> str:
    degree = _safe_degree(expr)
    if degree is None:
        return ""
    turns = _num_turning_points(expr)
    plural = "" if turns == 1 else "s"
    return f"A degree-{degree} curve with {turns} turning point{plural}."


def _trig_note(intent: TrigDirect) -> str:
    amplitude = sp.Abs(sp.sympify(intent.amplitude))
    shift = sp.sympify(intent.vertical_shift)
    low, high = sp.simplify(shift - amplitude), sp.simplify(shift + amplitude)
    swing = f"It swings between {_fmt(low)} and {_fmt(high)}"
    frequency = sp.Abs(sp.sympify(intent.frequency))
    if frequency == 0:
        return f"{swing}."
    period = sp.simplify(2 * sp.pi / frequency)
    return f"{swing} and repeats every {_fmt(period)}."


def _exponential_note(intent: ExponentialDirect) -> str:
    if isinstance(intent.base, str) and intent.base.strip().lower() == "e":
        base = sp.E
    else:
        base = sp.sympify(intent.base)
    factor = base ** sp.sympify(intent.rate)
    if factor.evalf() > 1:
        return "It grows faster and faster as you move right."
    return (
        f"It flattens out toward y = {_fmt(sp.sympify(intent.vertical_shift))} as you move right."
    )


def _log_note(derived: DerivedFunction) -> str:
    try:
        boundary = derived.domain.inf
    except (NotImplementedError, ValueError, TypeError):
        return "It grows slowly, and only for positive inputs."
    if boundary.is_finite:
        return f"It's only defined for x greater than {_fmt(boundary)}, and it grows slowly."
    return "It grows slowly, and only for positive inputs."


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #


def _fmt(value) -> str:
    e = sp.sympify(value)
    if e.is_Float:
        e = sp.nsimplify(e, rational=True)
    if e.is_Integer:
        text = str(int(e))
    elif e.is_Rational:
        text = f"{e.p}/{e.q}"
    else:
        text = sp.sstr(e).replace("pi", "π").replace("*π", "π")
    return text.replace("-", "−")  # real minus sign, matching the pretty equation


def _safe_degree(expr: sp.Expr) -> int | None:
    try:
        return int(sp.degree(sp.Poly(expr, x)))
    except (sp.PolynomialError, TypeError, ValueError):
        return None


def _num_turning_points(expr: sp.Expr) -> int:
    # Turning points = where the derivative is zero. Count *distinct* real roots
    # (a repeated root is a horizontal inflection, not a turn). real_solutions
    # stays correct for cubics+ where solve() returns roots in complex form.
    roots = real_solutions(sp.diff(expr, x))
    distinct: list[float] = []
    for r in roots:
        if not any(abs(r - d) < 1e-9 for d in distinct):
            distinct.append(r)
    return len(distinct)
