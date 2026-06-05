"""describe: the conversational result line (pretty equation + math note)."""

from app.do_the_math.describe import friendly_summary, pretty_equation
from app.do_the_math.ir import IntentWrapper
from app.do_the_math.math_engine import derive


def _summary(raw: dict) -> str:
    intent = IntentWrapper(intent=raw).intent
    return friendly_summary(intent, derive(intent))


def test_pretty_equation_uses_real_symbols():
    assert pretty_equation("y = 2*sin(3*x - 1)") == "y = 2·sin(3x − 1)"
    assert pretty_equation("y = (x - 1)**2 + 2") == "y = (x − 1)² + 2"
    assert pretty_equation("y = -x**3 + 2*x**2 + 5*x - 4") == "y = −x³ + 2x² + 5x − 4"
    assert pretty_equation("y = 2*x") == "y = 2x"
    assert pretty_equation("y = log(x)") == "y = ln(x)"


def test_sine_summary_is_playful_with_a_math_note():
    s = _summary({"kind": "trig", "func": "sin", "amplitude": 2, "frequency": 3, "phase": 1})
    assert "sine wave" in s
    assert "y = 2·sin(3x − 1)" in s  # pretty equation
    assert "swings between −2 and 2" in s
    assert "repeats every 2π/3" in s


def test_parabola_summary_names_the_vertex():
    s = _summary({"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"})
    assert "parabola" in s
    assert "vertex sits at (1, 2)" in s
    assert "opens upward" in s


def test_line_summary_describes_slope_and_intercept():
    s = _summary({"kind": "line_two_points", "point1": [0, 0], "point2": [2, 4]})
    assert "line" in s
    assert "y = 2x" in s
    assert "climbs 2" in s


def test_cubic_summary_reports_degree_and_turning_points():
    s = _summary({"kind": "polynomial", "coefficients": [-1, 2, 5, -4]})
    assert "cubic curve" in s
    assert "degree-3 curve with 2 turning points" in s


def test_monotonic_powers_have_no_turning_points():
    # f' has an even-multiplicity root at x=0 (an inflection, not a turn).
    assert "degree-3 curve with 0 turning points" in _summary(
        {"kind": "polynomial", "coefficients": [1, 0, 0, 0]}  # y = x**3
    )
    assert "degree-5 curve with 0 turning points" in _summary(
        {"kind": "polynomial", "coefficients": [1, 0, 0, 0, 0, 0]}  # y = x**5
    )


def test_even_power_has_one_turning_point():
    # y = x**4: f' = 4x**3 has an odd-multiplicity root at 0 -> a real turn (min).
    assert "degree-4 curve with 1 turning point" in _summary(
        {"kind": "polynomial", "coefficients": [1, 0, 0, 0, 0]}
    )


def test_quartic_turning_points_counted_in_casus_irreducibilis():
    # y = x^4 - 2x^3 - 5x^2 + 4x + 3: derivative is a cubic with three irrational
    # real roots that solve() returns in complex form. The count must still be 3.
    s = _summary({"kind": "polynomial", "coefficients": [1, -2, -5, 4, 3]})
    assert "degree-4 curve with 3 turning points" in s


def test_summary_never_empty_for_supported_kinds():
    for raw in [
        {"kind": "exponential", "base": "e"},
        {"kind": "logarithmic", "base": "e"},
        {"kind": "trig", "func": "cos"},
        {"kind": "quadratic_standard", "a": 1, "b": 0, "c": -4},
    ]:
        assert _summary(raw).strip()
