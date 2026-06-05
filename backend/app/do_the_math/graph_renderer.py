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

from .math_engine import DerivedFunction, x

_DEFAULT_RANGE = (-10.0, 10.0)
_NUM_POINTS = 1000


def _window(domain: sp.Set, default: tuple[float, float]) -> tuple[float, float]:
    """Clip the default x-window to a finite domain edge (e.g. log's x > 0)."""
    lo, hi = default
    try:
        inf, sup = domain.inf, domain.sup
    except (NotImplementedError, ValueError, TypeError):
        # Domains like tan's (Reals minus an infinite point set) have no
        # computable inf/sup — keep the default window; masking handles gaps.
        return lo, hi
    span = hi - lo
    eps = span * 1e-3
    if inf.is_finite and float(inf) > lo:
        lo = float(inf)
        if not domain.contains(sp.Float(lo)):  # open edge -> step just inside
            lo += eps
    if sup.is_finite and float(sup) < hi:
        hi = float(sup)
        if not domain.contains(sp.Float(hi)):
            hi -= eps
    return lo, hi


def _to_json(values: np.ndarray) -> list[float | None]:
    """Convert an array to a JSON-safe list (non-finite -> None)."""
    return [None if not np.isfinite(v) else float(v) for v in values]


def render(
    derived: DerivedFunction,
    x_range: tuple[float, float] | None = None,
    num_points: int = _NUM_POINTS,
) -> dict:
    """Render a derived function into a Plotly figure spec (plain dict)."""
    lo, hi = _window(derived.domain, x_range or _DEFAULT_RANGE)
    xs = np.linspace(lo, hi, num_points)

    f = sp.lambdify(x, derived.expr, modules=["numpy"])
    with np.errstate(all="ignore"):
        raw = f(xs)
    ys = np.asarray(raw, dtype="float64")
    if ys.ndim == 0 or ys.size == 1:  # constant expression -> broadcast
        ys = np.full_like(xs, float(ys))
    ys[~np.isfinite(ys)] = np.nan  # +/-inf -> nan (gap)

    ylo, yhi = _clip_asymptotes_and_range(ys)

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
            "title": {"text": derived.equation},
            "xaxis": {"title": {"text": "x"}, "zeroline": True, "range": [lo, hi]},
            "yaxis": {"title": {"text": "y"}, "zeroline": True, "range": [ylo, yhi]},
            "showlegend": False,
            "margin": {"t": 48, "r": 16, "b": 40, "l": 48},
        },
    }


def _clip_asymptotes_and_range(ys: np.ndarray) -> tuple[float, float]:
    """Mask asymptote spikes (in place) and return a robust y display range.

    Uses a spread (2nd-98th percentile of finite y) that adapts to the data:
    points far beyond a few spreads from the median are treated as asymptote
    blow-ups and set to NaN (creating gaps), while genuinely large but smooth
    functions (steep polynomials, exponentials) keep their whole curve.
    """
    finite = ys[np.isfinite(ys)]
    if finite.size == 0:
        return -10.0, 10.0

    p2, p98 = np.percentile(finite, [2, 98])
    median = float(np.median(finite))
    spread = max(float(p98 - p2), 1e-9)

    # Gap out values that explode far beyond the typical spread (asymptotes).
    ys[np.abs(ys - median) > 6.0 * spread] = np.nan

    pad = max(0.1 * spread, 1.0)
    ylo, yhi = float(p2) - pad, float(p98) + pad
    if ylo == yhi:  # constant function
        ylo, yhi = ylo - 1.0, yhi + 1.0
    return ylo, yhi
