"""Property-based tests on the math core (Hypothesis).

These guard the trust boundary with invariants that must hold for *any* valid
input, not just the hand-picked examples in the other suites:

- the human-readable ``equation`` string always re-parses to the exact same
  SymPy expression (what we show == what we computed);
- exact arithmetic is preserved — integer/rational/exact-float inputs never
  leave a stray ``Float`` in the derived expression;
- a degree-n polynomial has at most n-1 turning points (and never negative);
- a rendered figure is always JSON-safe — every y is a finite number or
  ``None`` (a masked gap), never NaN/Infinity; x values are always finite.
"""

import math

import pytest
import sympy as sp
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.do_the_math.describe import _num_turning_points
from app.do_the_math.errors import DerivationError, OutOfScopeError
from app.do_the_math.graph_renderer import render
from app.do_the_math.ir import IntentWrapper
from app.do_the_math.math_engine import derive, x

ints = st.integers(min_value=-12, max_value=12)
# Exact multiples of 1/4 — representable exactly in float64, so the engine's
# float -> Rational normalization must land on an exact number (no Float left).
quarters = st.integers(min_value=-40, max_value=40).map(lambda n: n / 4)


def _derive(intent_dict: dict):
    return derive(IntentWrapper(intent=intent_dict).intent)


def _round_trips(intent_dict: dict) -> bool:
    d = _derive(intent_dict)
    rhs = d.equation.split("=", 1)[1]
    # Parse against the engine's real-valued ``x`` so the symbols match.
    return sp.simplify(sp.sympify(rhs, locals={"x": x}) - d.expr) == 0


# --------------------------------------------------------------------------- #
# 1. The displayed equation always re-parses to the exact derived expression.
# --------------------------------------------------------------------------- #


@settings(deadline=None)
@given(coeffs=st.lists(ints, min_size=1, max_size=6))
def test_polynomial_equation_round_trips(coeffs):
    assert _round_trips({"kind": "polynomial", "coefficients": coeffs})


@settings(deadline=None)
@given(m=ints, b=ints)
def test_linear_equation_round_trips(m, b):
    assert _round_trips({"kind": "linear_direct", "slope": m, "intercept": b})


@settings(deadline=None)
@given(a=ints.filter(lambda v: v != 0), h=ints, k=ints)
def test_quadratic_vertex_equation_round_trips(a, h, k):
    assert _round_trips({"kind": "quadratic_vertex", "a": a, "h": h, "k": k})


@settings(deadline=None)
@given(
    func=st.sampled_from(["sin", "cos", "tan"]),
    amplitude=ints,
    frequency=ints,
    phase=ints,
    vertical_shift=ints,
)
def test_trig_equation_round_trips(func, amplitude, frequency, phase, vertical_shift):
    assert _round_trips(
        {
            "kind": "trig",
            "func": func,
            "amplitude": amplitude,
            "frequency": frequency,
            "phase": phase,
            "vertical_shift": vertical_shift,
        }
    )


@settings(deadline=None)
@given(base=st.sampled_from(["e", 2, 3]), coefficient=ints, rate=st.integers(-4, 4), shift=ints)
def test_exponential_equation_round_trips(base, coefficient, rate, shift):
    assert _round_trips(
        {
            "kind": "exponential",
            "base": base,
            "coefficient": coefficient,
            "rate": rate,
            "vertical_shift": shift,
        }
    )


# --------------------------------------------------------------------------- #
# 2. Exact arithmetic is preserved (no Float pollution).
# --------------------------------------------------------------------------- #


@given(coeffs=st.lists(quarters, min_size=1, max_size=5))
def test_exact_float_inputs_stay_exact(coeffs):
    d = _derive({"kind": "polynomial", "coefficients": coeffs})
    assert not d.expr.atoms(sp.Float)


@given(a=quarters.filter(lambda v: v != 0), h=quarters, k=quarters)
def test_quadratic_vertex_stays_exact(a, h, k):
    d = _derive({"kind": "quadratic_vertex", "a": a, "h": h, "k": k})
    assert not d.expr.atoms(sp.Float)


# --------------------------------------------------------------------------- #
# 3. A degree-n polynomial has between 0 and n-1 turning points.
# --------------------------------------------------------------------------- #


@settings(deadline=None)
@given(coeffs=st.lists(ints, min_size=2, max_size=6))
def test_turning_points_bounded_by_degree(coeffs):
    assume(coeffs[0] != 0)  # genuine degree = len - 1
    degree = len(coeffs) - 1
    turns = _num_turning_points(_derive({"kind": "polynomial", "coefficients": coeffs}).expr)
    assert 0 <= turns <= degree - 1


# --------------------------------------------------------------------------- #
# 4. Rendered figures are always JSON-safe (no NaN/Infinity).
# --------------------------------------------------------------------------- #


def _assert_json_safe(figure: dict) -> None:
    series = figure["data"][0]
    xs, ys = series["x"], series["y"]
    assert len(xs) == len(ys)
    assert all(math.isfinite(v) for v in xs)
    assert all(v is None or math.isfinite(v) for v in ys)


@settings(deadline=None, max_examples=40)
@given(coeffs=st.lists(ints, min_size=1, max_size=5))
def test_rendered_polynomial_is_json_safe(coeffs):
    _assert_json_safe(
        render(_derive({"kind": "polynomial", "coefficients": coeffs}), num_points=200)
    )


@settings(deadline=None, max_examples=40)
@given(func=st.sampled_from(["sin", "cos", "tan"]), amplitude=ints, frequency=st.integers(1, 6))
def test_rendered_trig_is_json_safe(func, amplitude, frequency):
    # tan exercises the asymptote masking; the contract is finite-or-None.
    figure = render(
        _derive(
            {
                "kind": "trig",
                "func": func,
                "amplitude": amplitude,
                "frequency": frequency,
                "phase": 0,
                "vertical_shift": 0,
            }
        ),
        num_points=200,
    )
    _assert_json_safe(figure)


@settings(deadline=None, max_examples=40)
@given(
    base=st.sampled_from(["e", "10", 2, 3]),
    coefficient=st.integers(-6, 6),
    inner_coeff=st.integers(1, 6),
    h_shift=ints,
    vertical_shift=ints,
)
def test_rendered_log_is_json_safe(base, coefficient, inner_coeff, h_shift, vertical_shift):
    # log exercises domain clamping (argument must be positive).
    figure = render(
        _derive(
            {
                "kind": "logarithmic",
                "base": base,
                "coefficient": coefficient,
                "inner_coeff": inner_coeff,
                "h_shift": h_shift,
                "vertical_shift": vertical_shift,
            }
        ),
        num_points=200,
    )
    _assert_json_safe(figure)


# --------------------------------------------------------------------------- #
# 5. Honest refusal — degenerate inputs always raise, never a wrong graph.
#    And every successful derivation is a real function of x alone.
# --------------------------------------------------------------------------- #


@given(b=ints, c=ints)
def test_zero_a_quadratic_always_refused(b, c):
    with pytest.raises(DerivationError):
        _derive({"kind": "quadratic_standard", "a": 0, "b": b, "c": c})
    with pytest.raises(DerivationError):
        _derive({"kind": "quadratic_vertex", "a": 0, "h": b, "k": c})


@given(x0=ints, y1=ints, y2=ints)
def test_vertical_line_always_refused(x0, y1, y2):
    assume(y1 != y2)  # two distinct points sharing an x = a vertical line
    with pytest.raises(OutOfScopeError):
        _derive({"kind": "line_two_points", "point1": [x0, y1], "point2": [x0, y2]})


@given(base=st.sampled_from([0, 1, -1, -2, -10]), coefficient=ints, rate=st.integers(-3, 3))
def test_bad_exponential_base_always_refused(base, coefficient, rate):
    # base must be positive and != 1.
    with pytest.raises(DerivationError):
        _derive(
            {
                "kind": "exponential",
                "base": base,
                "coefficient": coefficient,
                "rate": rate,
                "vertical_shift": 0,
            }
        )


@settings(deadline=None)
@given(coeffs=st.lists(ints, min_size=1, max_size=6))
def test_derived_polynomial_is_a_function_of_x_alone(coeffs):
    # A successful derivation never smuggles in another variable.
    d = _derive({"kind": "polynomial", "coefficients": coeffs})
    assert d.expr.free_symbols <= {x}
