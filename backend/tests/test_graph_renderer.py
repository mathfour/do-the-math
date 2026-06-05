"""graph_renderer: JSON-safety, asymptote gaps, domain clipping."""

import json

from app.do_the_math.graph_renderer import render
from app.do_the_math.ir import IntentWrapper
from app.do_the_math.math_engine import derive


def _fig(raw: dict) -> dict:
    return render(derive(IntentWrapper(intent=raw).intent))


def test_figure_is_json_serializable_without_nan():
    fig = _fig({"kind": "trig", "func": "tan"})
    # NaN/Infinity are invalid JSON; allow_nan=False must succeed.
    json.dumps(fig, allow_nan=False)


def test_figure_has_expected_plotly_shape():
    fig = _fig({"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"})
    trace = fig["data"][0]
    assert trace["type"] == "scatter"
    assert trace["mode"] == "lines"
    assert trace["connectgaps"] is False
    assert fig["layout"]["title"]["text"] == "y = (x − 1)² + 2"  # pretty form


def test_parabola_has_no_gaps():
    fig = _fig({"kind": "parabola_vertex_direction", "vertex": [0, 0], "direction": "up"})
    assert all(v is not None for v in fig["data"][0]["y"])


def test_tan_has_asymptote_gaps():
    fig = _fig({"kind": "trig", "func": "tan"})
    assert any(v is None for v in fig["data"][0]["y"])


def test_log_window_clipped_to_positive_x():
    fig = _fig({"kind": "logarithmic", "base": "e"})
    lo, _ = fig["layout"]["xaxis"]["range"]
    assert lo > 0


def test_steep_polynomial_not_masked():
    # x**8 is large but smooth — it must not be mistaken for an asymptote.
    fig = _fig({"kind": "polynomial", "coefficients": [1, 0, 0, 0, 0, 0, 0, 0, 0]})
    assert all(v is not None for v in fig["data"][0]["y"])


def test_cubic_window_focuses_on_turning_points():
    # y = -x^3 + 2x^2 + 5x - 4 has turning points near x=-0.8 and x=2.1; the
    # window should frame them (not the default [-10, 10] where the tails dominate)
    # so the peak/valley (|y| ~ 6) are visible rather than dwarfed.
    fig = _fig({"kind": "polynomial", "coefficients": [-1, 2, 5, -4]})
    lo, hi = fig["layout"]["xaxis"]["range"]
    assert lo > -6 and hi < 7  # zoomed in from the default
    ylo, yhi = fig["layout"]["yaxis"]["range"]
    assert max(abs(ylo), abs(yhi)) < 60  # not the ~1000 of the default window


def test_wiggly_quartic_frames_the_hills_and_valleys():
    # The window frames the 3 turning points, and the y-range frames the local
    # extrema so the steep x^4 tails clip instead of flattening the wiggle.
    fig = _fig({"kind": "polynomial", "coefficients": [1, -2, -5, 4, 3]})
    lo, hi = fig["layout"]["xaxis"]["range"]
    assert lo > -6 and hi < 7
    ylo, yhi = fig["layout"]["yaxis"]["range"]
    assert yhi < 60  # not the ~10k of the default window where the tails dominate


def test_far_vertex_parabola_is_centered_on_vertex():
    fig = _fig({"kind": "parabola_vertex_direction", "vertex": [50, 3], "direction": "up"})
    lo, hi = fig["layout"]["xaxis"]["range"]
    assert lo < 50 < hi  # window follows the vertex instead of staying at the origin


def test_constant_function_renders_finite_range():
    fig = _fig({"kind": "linear_direct", "slope": 0, "intercept": 5})
    lo, hi = fig["layout"]["yaxis"]["range"]
    assert lo < hi
    assert all(v == 5 for v in fig["data"][0]["y"])
