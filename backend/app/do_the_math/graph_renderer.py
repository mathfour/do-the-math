"""Validated math -> a JSON-serializable Plotly figure spec.

Samples the derived function over a domain-aware window, filters non-finite
values, opens gaps at asymptotes (so e.g. ``tan`` doesn't draw vertical
spikes), and returns a plain ``dict`` ready to drop into the envelope payload.
The dict contains no NaN/Infinity (invalid JSON): non-finite y-values become
``None`` and Plotly is told not to connect across gaps.
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from .formatting import pretty_equation
from .math_engine import DerivedFunction, real_solutions, x

_DEFAULT_RANGE = (-10.0, 10.0)
_NUM_POINTS = 1000


def _clamp_to_domain(domain: sp.Set, window: tuple[float, float]) -> tuple[float, float]:
    """Clip a candidate x-window to a finite domain edge (e.g. log's x > 0)."""
    lo, hi = window
    try:
        inf, sup = domain.inf, domain.sup
    except (NotImplementedError, ValueError, TypeError):
        # Domains like tan's (Reals minus an infinite point set) have no
        # computable inf/sup — keep the window; masking handles gaps.
        return lo, hi
    eps = (hi - lo) * 1e-3
    if inf.is_finite and float(inf) > lo:
        lo = float(inf)
        if not domain.contains(sp.Float(lo)):  # open edge -> step just inside
            lo += eps
    if sup.is_finite and float(sup) < hi:
        hi = float(sup)
        if not domain.contains(sp.Float(hi)):
            hi -= eps
    return lo, hi


def _feature_window(expr: sp.Expr, domain: sp.Set, critical: list[float]) -> tuple[float, float]:
    """Pick an x-window around the function's interesting features.

    Turning points (where the derivative is zero) are what make peaks and
    valleys visible; without them a fixed window lets a polynomial's tails
    dwarf the shape. Falls back to roots, then to the default window.
    """
    anchors = critical or real_solutions(expr)
    if not anchors:
        return _clamp_to_domain(domain, _DEFAULT_RANGE)

    lo, hi = min(anchors), max(anchors)
    if hi - lo < 1e-9:  # a single feature (e.g. a vertex) -> view a band around it
        lo, hi = lo - 6.0, hi + 6.0
    else:
        pad = 0.6 * (hi - lo)
        lo, hi = lo - pad, hi + pad
    return _clamp_to_domain(domain, (lo, hi))


def _to_json(values: np.ndarray) -> list[float | None]:
    """Convert an array to a JSON-safe list (non-finite -> None)."""
    return [None if not np.isfinite(v) else float(v) for v in values]


def render(
    derived: DerivedFunction,
    x_range: tuple[float, float] | None = None,
    num_points: int = _NUM_POINTS,
) -> dict:
    """Render a derived function into a Plotly figure spec (plain dict)."""
    critical = real_solutions(sp.diff(derived.expr, x))
    lo, hi = (
        _clamp_to_domain(derived.domain, x_range)
        if x_range is not None
        else _feature_window(derived.expr, derived.domain, critical)
    )
    xs = np.linspace(lo, hi, num_points)

    f = sp.lambdify(x, derived.expr, modules=["numpy"])
    with np.errstate(all="ignore"):
        raw = f(xs)
    ys = np.asarray(raw, dtype="float64")
    if ys.ndim == 0 or ys.size == 1:  # constant expression -> broadcast
        ys = np.full_like(xs, float(ys))
    ys[~np.isfinite(ys)] = np.nan  # +/-inf -> nan (gap)

    _mask_asymptotes(ys)
    ylo, yhi = _y_range(f, critical, lo, hi, ys)

    return {
        "data": [
            {
                "type": "scatter",
                "mode": "lines",
                "x": _to_json(xs),
                "y": _to_json(ys),
                "name": derived.equation,
                "connectgaps": False,
            }
        ],
        "layout": {
            "title": {"text": pretty_equation(derived.equation)},
            "xaxis": {"title": {"text": "x"}, "zeroline": True, "range": [lo, hi]},
            "yaxis": {"title": {"text": "y"}, "zeroline": True, "range": [ylo, yhi]},
            "showlegend": False,
            "margin": {"t": 48, "r": 16, "b": 40, "l": 48},
        },
    }


def _mask_asymptotes(ys: np.ndarray) -> None:
    """Gap out (in place) values that explode far beyond the typical spread.

    This is what opens vertical gaps at ``tan``/rational asymptotes while
    leaving genuinely large-but-smooth curves (steep polynomials) intact.
    """
    finite = ys[np.isfinite(ys)]
    if finite.size == 0:
        return
    p2, p98 = np.percentile(finite, [2, 98])
    median = float(np.median(finite))
    spread = max(float(p98 - p2), 1e-9)
    ys[np.abs(ys - median) > 6.0 * spread] = np.nan


def _y_range(f, critical: list[float], lo: float, hi: float, ys: np.ndarray) -> tuple[float, float]:
    """Choose the y display range.

    When the function has two or more turning points in view (a wiggly
    polynomial), frame the hills and valleys themselves — the local extrema —
    so steep tails clip off-screen instead of flattening the interesting part.
    Otherwise use a robust percentile band of the sampled values.
    """
    extrema = _distinct([c for c in critical if lo <= c <= hi])
    if len(extrema) >= 2:
        with np.errstate(all="ignore"):
            heights = [float(f(c)) for c in extrema]
        heights = [h for h in heights if np.isfinite(h)]
        if len(heights) >= 2 and max(heights) > min(heights):
            pad = 0.35 * (max(heights) - min(heights))
            return min(heights) - pad, max(heights) + pad

    finite = ys[np.isfinite(ys)]
    if finite.size == 0:
        return -10.0, 10.0
    p2, p98 = np.percentile(finite, [2, 98])
    spread = max(float(p98 - p2), 1e-9)
    pad = max(0.1 * spread, 1.0)
    ylo, yhi = float(p2) - pad, float(p98) + pad
    if ylo == yhi:  # constant function
        ylo, yhi = ylo - 1.0, yhi + 1.0
    return ylo, yhi


def _distinct(values: list[float], tol: float = 1e-9) -> list[float]:
    out: list[float] = []
    for v in values:
        if not any(abs(v - u) < tol for u in out):
            out.append(v)
    return out
