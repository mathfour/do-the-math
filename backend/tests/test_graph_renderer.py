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
    assert fig["layout"]["title"]["text"] == "y = (x - 1)**2 + 2"


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


def test_constant_function_renders_finite_range():
    fig = _fig({"kind": "linear_direct", "slope": 0, "intercept": 5})
    lo, hi = fig["layout"]["yaxis"]["range"]
    assert lo < hi
    assert all(v == 5 for v in fig["data"][0]["y"])
