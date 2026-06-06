"""IR -> validated math. SymPy is the source of mathematical truth.

``derive(intent)`` turns a Math Intent into a canonical ``y = f(x)`` SymPy
expression (kept *exact* — Rational/Integer, never float-littered), a readable
equation string, and the function's natural domain. Out-of-scope or inconsistent
requests raise rather than returning a wrong graph.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from .errors import DerivationError, OutOfScopeError
from .ir import (
    ExponentialDirect,
    LinearDirect,
    LinePointSlope,
    LineTwoPoints,
    LogarithmicDirect,
    MathIntent,
    ParabolaThreePoints,
    ParabolaVertexDirection,
    ParabolaVertexPoint,
    PolynomialDirect,
    QuadraticStandard,
    QuadraticVertex,
    TrigDirect,
    Unsupported,
)

# The single independent variable. ``real=True`` keeps domains/solves sane.
x = sp.Symbol("x", real=True)

_UNSUPPORTED_MESSAGE = {
    "implicit": (
        "Circles and similar shapes — where y isn't written by itself, "
        "like x² + y² = 25 — aren't something I can graph yet."
    ),
    "parametric": (
        "Curves traced by a moving point — where x and y each follow their own "
        "recipe — aren't something I can graph yet."
    ),
    "polar": "Spiral and flower-shaped 'polar' graphs aren't something I can graph yet.",
    "piecewise": (
        'Functions that switch rules over different stretches of x ("piecewise" '
        "functions) aren't something I can graph yet."
    ),
    "inequality": "Inequalities and shaded regions aren't something I can graph yet.",
    "not_a_function": (
        "That isn't a function — to graph it this way I need exactly one y for each "
        "x — so I can't draw it yet."
    ),
    "unknown": (
        'Future versions of "Do the Math" will be able to do more robust math things. '
        "Stay tuned!"
    ),
}


@dataclass(frozen=True)
class DerivedFunction:
    """The validated result of deriving an IR into a function of ``x``."""

    expr: sp.Expr  # canonical f(x), exact
    equation: str  # e.g. "y = (x - 1)**2 + 2"
    kind: str  # echoes the IR kind
    domain: sp.Set  # natural (continuous) domain over the reals


# --------------------------------------------------------------------------- #
# Exact numeric normalization — the most important math-core invariant.
# --------------------------------------------------------------------------- #


def _num(value) -> sp.Expr:
    """Normalize an IR number to an *exact* SymPy number.

    ``int`` -> Integer, ``float`` -> exact Rational (0.5 -> 1/2),
    ``str`` -> ``sympify`` (handles "1/3", "sqrt(2)", "e", "pi").
    Rejects booleans and anything that isn't a finite real constant.
    """
    if isinstance(value, bool):
        raise DerivationError(f"Expected a number, got boolean {value!r}.")
    if isinstance(value, int):
        return sp.Integer(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise DerivationError(f"Non-finite number: {value!r}.")
        return sp.nsimplify(sp.Float(value), rational=True)
    if isinstance(value, str):
        try:
            expr = sp.sympify(value, rational=True)
        except (sp.SympifyError, SyntaxError, TypeError) as exc:
            raise DerivationError(f"Could not parse number {value!r}.") from exc
        if expr.free_symbols:
            raise DerivationError(f"Numeric field {value!r} contains a variable.")
        if not expr.is_finite:
            raise DerivationError(f"Non-finite number: {value!r}.")
        return expr
    raise DerivationError(f"Unsupported numeric type: {type(value).__name__}.")


def _pt(point) -> tuple[sp.Expr, sp.Expr]:
    return _num(point[0]), _num(point[1])


def _resolve_base(base) -> sp.Expr:
    if isinstance(base, str) and base.strip().lower() == "e":
        return sp.E
    b = _num(base)
    if b.is_positive is False or b == 0:
        raise DerivationError("A log or exponential needs a positive base.")
    if b == 1:
        raise DerivationError("A log or exponential can't use a base of 1.")
    return b


# --------------------------------------------------------------------------- #
# Per-kind derivation handlers (return a SymPy expr in x).
# --------------------------------------------------------------------------- #


def _linear_direct(ir: LinearDirect) -> sp.Expr:
    return _num(ir.slope) * x + _num(ir.intercept)


def _quadratic_vertex(ir: QuadraticVertex) -> sp.Expr:
    a = _num(ir.a)
    if a == 0:
        raise DerivationError("With a flat (zero) leading number that's a line, not a parabola.")
    return a * (x - _num(ir.h)) ** 2 + _num(ir.k)


def _quadratic_standard(ir: QuadraticStandard) -> sp.Expr:
    a = _num(ir.a)
    if a == 0:
        raise DerivationError("With a flat (zero) leading number that's a line, not a parabola.")
    return a * x**2 + _num(ir.b) * x + _num(ir.c)


def _polynomial(ir: PolynomialDirect) -> sp.Expr:
    coeffs = [_num(c) for c in ir.coefficients]
    degree = len(coeffs) - 1
    return sum((c * x ** (degree - i) for i, c in enumerate(coeffs)), sp.Integer(0))


def _trig(ir: TrigDirect) -> sp.Expr:
    func = {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan}[ir.func]
    a = _num(ir.amplitude)
    b = _num(ir.frequency)
    c = _num(ir.phase)
    d = _num(ir.vertical_shift)
    return a * func(b * x - c) + d


def _exponential(ir: ExponentialDirect) -> sp.Expr:
    base = _resolve_base(ir.base)
    a = _num(ir.coefficient)
    b = _num(ir.rate)
    d = _num(ir.vertical_shift)
    return a * base ** (b * x) + d


def _logarithmic(ir: LogarithmicDirect) -> sp.Expr:
    base = _resolve_base(ir.base)
    a = _num(ir.coefficient)
    b = _num(ir.inner_coeff)
    h = _num(ir.h_shift)
    d = _num(ir.vertical_shift)
    arg = b * (x - h)
    log_expr = sp.log(arg) if base == sp.E else sp.log(arg) / sp.log(base)
    return a * log_expr + d


def _line_two_points(ir: LineTwoPoints) -> sp.Expr:
    (x1, y1), (x2, y2) = _pt(ir.point1), _pt(ir.point2)
    if x1 == x2:
        raise OutOfScopeError(
            "not_a_function",
            "A vertical line (like x = 3) isn't a function — it has many y-values at "
            "a single x — so I can't graph it yet.",
        )
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return slope * x + intercept


def _line_point_slope(ir: LinePointSlope) -> sp.Expr:
    px, py = _pt(ir.point)
    return _num(ir.slope) * (x - px) + py


def _parabola_vertex_direction(ir: ParabolaVertexDirection) -> sp.Expr:
    h, k = _pt(ir.vertex)
    magnitude = sp.Integer(1) if ir.a_magnitude is None else _num(ir.a_magnitude)
    if magnitude <= 0:
        raise DerivationError("The parabola's stretch needs to be a positive amount.")
    a = magnitude if ir.direction == "up" else -magnitude
    return a * (x - h) ** 2 + k


def _parabola_vertex_point(ir: ParabolaVertexPoint) -> sp.Expr:
    h, k = _pt(ir.vertex)
    px, py = _pt(ir.point)
    if px == h:
        raise DerivationError(
            "That extra point sits straight above or below the vertex, so I can't tell "
            "how wide the parabola is. Try a point with a different x."
        )
    a_sym = sp.Symbol("a")
    solutions = sp.solve(sp.Eq(py, a_sym * (px - h) ** 2 + k), a_sym)
    if not solutions:
        raise DerivationError("No parabola passes through both that vertex and that point.")
    a = solutions[0]
    if a == 0:
        raise DerivationError("That vertex and point line up flat — that's a line, not a parabola.")
    return a * (x - h) ** 2 + k


def _parabola_three_points(ir: ParabolaThreePoints) -> sp.Expr:
    pts = [_pt(p) for p in ir.points]
    if len(set(pts)) < 3:
        raise DerivationError("Please give three different points for the parabola.")
    # Two points sharing an x-value can't both lie on a function y = f(x).
    if len({px for px, _ in pts}) < 3:
        raise OutOfScopeError(
            "not_a_function",
            "Two of those points sit at the same x, so no single curve can pass "
            "through all three.",
        )
    a_s, b_s, c_s = sp.symbols("a b c")
    equations = [sp.Eq(py, a_s * px**2 + b_s * px + c_s) for px, py in pts]
    solution = sp.linsolve(equations, (a_s, b_s, c_s))
    if not solution:
        raise OutOfScopeError(
            "not_a_function",
            "Those three points don't make a parabola (they line up straight, or repeat).",
        )
    a, b, c = next(iter(solution))
    if a == 0:
        raise OutOfScopeError(
            "not_a_function",
            "Those three points line up straight — that's a line, not a parabola.",
        )
    return a * x**2 + b * x + c


_HANDLERS = {
    "linear_direct": _linear_direct,
    "quadratic_vertex": _quadratic_vertex,
    "quadratic_standard": _quadratic_standard,
    "polynomial": _polynomial,
    "trig": _trig,
    "exponential": _exponential,
    "logarithmic": _logarithmic,
    "line_two_points": _line_two_points,
    "line_point_slope": _line_point_slope,
    "parabola_vertex_direction": _parabola_vertex_direction,
    "parabola_vertex_point": _parabola_vertex_point,
    "parabola_three_points": _parabola_three_points,
}


# --------------------------------------------------------------------------- #
# Public entry point.
# --------------------------------------------------------------------------- #


def _natural_domain(expr: sp.Expr) -> sp.Set:
    try:
        return sp.calculus.util.continuous_domain(expr, x, sp.S.Reals)
    except (NotImplementedError, ValueError, TypeError):
        return sp.S.Reals


def _guard(expr: sp.Expr) -> None:
    """Reject anything that isn't a real single-variable function of x."""
    # Catch genuine relations/booleans (x > 0, Eq(...), And/Or, True/False) —
    # but NOT a bare Symbol, which is itself a ``Boolean`` instance in SymPy
    # (so ``isinstance(x, Boolean)`` is True and would wrongly reject y = x).
    if expr.is_Relational or isinstance(
        expr, (sp.logic.boolalg.BooleanFunction, sp.logic.boolalg.BooleanAtom)
    ):
        raise OutOfScopeError(
            "not_a_function", "That describes a relation, not a function y = f(x)."
        )
    extra = expr.free_symbols - {x}
    if extra:
        names = ", ".join(sorted(str(s) for s in extra))
        raise DerivationError(f"Derived expression has unexpected variables: {names}.")
    if expr.has(sp.Piecewise):
        raise OutOfScopeError("piecewise", _UNSUPPORTED_MESSAGE["piecewise"])


def derive(intent: MathIntent) -> DerivedFunction:
    """Derive and validate an IR into a function of ``x``.

    Raises ``OutOfScopeError`` for unsupported requests and ``DerivationError``
    for structurally-valid-but-underivable ones. Never returns a wrong graph.
    """
    if isinstance(intent, Unsupported):
        raise OutOfScopeError(intent.reason, _UNSUPPORTED_MESSAGE.get(intent.reason, intent.detail))

    handler = _HANDLERS.get(intent.kind)
    if handler is None:  # pragma: no cover - guarded by the typed union
        raise DerivationError(f"No handler for IR kind {intent.kind!r}.")

    expr = sp.sympify(handler(intent))
    _guard(expr)
    equation = "y = " + sp.sstr(expr)
    return DerivedFunction(
        expr=expr, equation=equation, kind=intent.kind, domain=_natural_domain(expr)
    )


def real_solutions(expr: sp.Expr) -> list[float]:
    """Sorted real, finite numeric solutions of ``expr == 0`` (best-effort).

    For polynomials, uses real-root isolation, which stays correct in the
    *casus irreducibilis* — where three real cubic roots come back in complex
    radical form that ``.is_real`` cannot classify (it returns ``None``), so a
    naive ``solve`` + ``is_real`` filter silently drops them. Non-polynomials
    fall back to ``solve`` with a numeric realness check.
    """
    if not getattr(expr, "free_symbols", None):
        return []
    try:
        poly = sp.Poly(expr, x)
    except (sp.PolynomialError, TypeError):
        poly = None
    if poly is not None and poly.degree() >= 1:
        try:
            return sorted(float(r) for r in sp.real_roots(poly))
        except (TypeError, ValueError, NotImplementedError):
            pass

    try:
        candidates = sp.solve(sp.Eq(expr, 0), x)
    except (NotImplementedError, ValueError, TypeError, RecursionError):
        return []
    if not isinstance(candidates, (list, tuple)):  # e.g. a ConditionSet
        return []
    out: list[float] = []
    for sol in candidates:
        try:
            value = complex(sol.evalf())
        except (TypeError, ValueError):
            continue
        if abs(value.imag) < 1e-9:
            out.append(float(value.real))
    return sorted(out)
