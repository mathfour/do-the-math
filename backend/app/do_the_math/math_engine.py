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
    "implicit": "Implicit equations (like x**2 + y**2 = 25) aren't supported in v1.",
    "parametric": "Parametric curves aren't supported in v1.",
    "polar": "Polar graphs aren't supported in v1.",
    "piecewise": "Piecewise functions aren't supported in v1.",
    "inequality": "Inequalities and shaded regions aren't supported in v1.",
    "not_a_function": "That isn't a function of the form y = f(x), so it can't be graphed in v1.",
    "unknown": "That request isn't something Do the Math supports in v1.",
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
        raise DerivationError("Logarithm/exponential base must be positive.")
    if b == 1:
        raise DerivationError("Logarithm/exponential base cannot be 1.")
    return b


# --------------------------------------------------------------------------- #
# Per-kind derivation handlers (return a SymPy expr in x).
# --------------------------------------------------------------------------- #


def _linear_direct(ir: LinearDirect) -> sp.Expr:
    return _num(ir.slope) * x + _num(ir.intercept)


def _quadratic_vertex(ir: QuadraticVertex) -> sp.Expr:
    a = _num(ir.a)
    if a == 0:
        raise DerivationError("A quadratic needs a nonzero leading coefficient (a != 0).")
    return a * (x - _num(ir.h)) ** 2 + _num(ir.k)


def _quadratic_standard(ir: QuadraticStandard) -> sp.Expr:
    a = _num(ir.a)
    if a == 0:
        raise DerivationError("A quadratic needs a nonzero leading coefficient (a != 0).")
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
            "A vertical line (x = constant) isn't a function y = f(x), so it can't "
            "be graphed in v1.",
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
        raise DerivationError("Parabola stretch magnitude must be positive.")
    a = magnitude if ir.direction == "up" else -magnitude
    return a * (x - h) ** 2 + k


def _parabola_vertex_point(ir: ParabolaVertexPoint) -> sp.Expr:
    h, k = _pt(ir.vertex)
    px, py = _pt(ir.point)
    if px == h:
        raise DerivationError(
            "The extra point lies on the parabola's axis of symmetry, so the "
            "stretch can't be determined. Give a point with a different x-value."
        )
    a_sym = sp.Symbol("a")
    solutions = sp.solve(sp.Eq(py, a_sym * (px - h) ** 2 + k), a_sym)
    if not solutions:
        raise DerivationError("No parabola fits that vertex and point.")
    a = solutions[0]
    if a == 0:
        raise DerivationError("That vertex and point describe a horizontal line, not a parabola.")
    return a * (x - h) ** 2 + k


def _parabola_three_points(ir: ParabolaThreePoints) -> sp.Expr:
    pts = [_pt(p) for p in ir.points]
    a_s, b_s, c_s = sp.symbols("a b c")
    equations = [sp.Eq(py, a_s * px**2 + b_s * px + c_s) for px, py in pts]
    solution = sp.linsolve(equations, (a_s, b_s, c_s))
    if not solution:
        raise OutOfScopeError(
            "not_a_function",
            "Those three points don't define a parabola (they may be collinear or repeated).",
        )
    a, b, c = next(iter(solution))
    if a == 0:
        raise OutOfScopeError(
            "not_a_function",
            "Those three points are collinear — that's a line, not a parabola.",
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
    if isinstance(expr, sp.logic.boolalg.Boolean) or expr.is_Relational:
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
