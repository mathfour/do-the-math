"""math_engine: derivation correctness, exact arithmetic, scope rejection.

These are pure SymPy tests (no provider) — the trust core. The math must be
correct on screen, so several assert the exact equation string.
"""

import pytest
import sympy as sp

from app.do_the_math.errors import DerivationError, OutOfScopeError
from app.do_the_math.ir import IntentWrapper
from app.do_the_math.math_engine import derive, x


def _derive(raw: dict):
    return derive(IntentWrapper(intent=raw).intent)


# --- Genuine derivations (the demo narrative) ------------------------------- #


def test_parabola_vertex_direction_up_exact_string():
    # README acceptance criterion.
    d = _derive({"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"})
    assert d.equation == "y = (x - 1)**2 + 2"


def test_parabola_opening_down_has_negative_leading_coefficient():
    d = _derive({"kind": "parabola_vertex_direction", "vertex": [0, 0], "direction": "down"})
    assert sp.Poly(d.expr, x).LC() < 0


def test_line_through_two_points():
    d = _derive({"kind": "line_two_points", "point1": [0, 0], "point2": [2, 4]})
    assert d.equation == "y = 2*x"


def test_parabola_from_vertex_and_point_solves_leading_coeff():
    d = _derive({"kind": "parabola_vertex_point", "vertex": [0, 0], "point": [1, 3]})
    assert d.equation == "y = 3*x**2"


def test_parabola_three_points():
    d = _derive({"kind": "parabola_three_points", "points": [[0, 0], [1, 1], [2, 4]]})
    assert sp.simplify(d.expr - x**2) == 0


def test_line_point_slope():
    d = _derive({"kind": "line_point_slope", "point": [0, 1], "slope": 2})
    assert sp.simplify(d.expr - (2 * x + 1)) == 0


# --- Exact arithmetic (the key invariant) ----------------------------------- #


def test_rational_slope_stays_exact():
    d = _derive({"kind": "linear_direct", "slope": "1/3", "intercept": 0})
    assert d.equation == "y = x/3"
    assert d.expr.coeff(x) == sp.Rational(1, 3)


def test_float_normalized_to_rational():
    d = _derive({"kind": "linear_direct", "slope": 0.5, "intercept": 0})
    assert d.expr.coeff(x) == sp.Rational(1, 2)


# --- Function families ------------------------------------------------------ #


def test_trig_sin_with_amplitude():
    d = _derive({"kind": "trig", "func": "sin", "amplitude": 2})
    assert d.equation == "y = 2*sin(x)"


def test_logarithmic_natural_domain_excludes_nonpositive():
    d = _derive({"kind": "logarithmic", "base": "e"})
    assert d.domain == sp.Interval.open(0, sp.oo)


def test_exponential_default_base_e():
    d = _derive({"kind": "exponential", "base": "e"})
    assert d.expr.free_symbols == {x}


def test_polynomial_highest_degree_first():
    d = _derive({"kind": "polynomial", "coefficients": [1, 0, -1]})  # x**2 - 1
    assert sp.simplify(d.expr - (x**2 - 1)) == 0


# --- Scope rejection (never a wrong graph) ---------------------------------- #


def test_vertical_line_is_not_a_function():
    with pytest.raises(OutOfScopeError) as exc:
        _derive({"kind": "line_two_points", "point1": [1, 0], "point2": [1, 5]})
    assert exc.value.reason == "not_a_function"


def test_collinear_three_points_rejected():
    with pytest.raises(OutOfScopeError) as exc:
        _derive({"kind": "parabola_three_points", "points": [[0, 0], [1, 1], [2, 2]]})
    assert exc.value.reason == "not_a_function"


def test_three_points_with_duplicates_get_clean_message():
    with pytest.raises(DerivationError) as exc:
        _derive({"kind": "parabola_three_points", "points": [[0, 0], [0, 0], [1, 1]]})
    assert "different" in exc.value.message.lower()


def test_three_points_sharing_an_x_value_rejected():
    with pytest.raises(OutOfScopeError) as exc:
        _derive({"kind": "parabola_three_points", "points": [[0, 0], [0, 1], [1, 2]]})
    assert exc.value.reason == "not_a_function"


def test_unsupported_implicit_raises_out_of_scope():
    with pytest.raises(OutOfScopeError) as exc:
        _derive({"kind": "unsupported", "reason": "implicit", "detail": "circle"})
    assert exc.value.reason == "implicit"
    # Plain-language message (no jargon like "implicit").
    assert "circle" in exc.value.message.lower()
    assert "implicit" not in exc.value.message.lower()


def test_zero_leading_coefficient_quadratic_rejected():
    with pytest.raises(DerivationError):
        _derive({"kind": "quadratic_standard", "a": 0, "b": 1, "c": 2})


def test_vertex_point_on_axis_rejected():
    with pytest.raises(DerivationError):
        _derive({"kind": "parabola_vertex_point", "vertex": [0, 0], "point": [0, 5]})


def test_numeric_field_with_variable_rejected():
    with pytest.raises(DerivationError):
        _derive({"kind": "linear_direct", "slope": "x", "intercept": 0})


def test_log_base_one_rejected():
    with pytest.raises(DerivationError):
        _derive({"kind": "logarithmic", "base": "1"})
