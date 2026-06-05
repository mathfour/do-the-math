"""Shared equation formatting.

``pretty_equation`` typesets the canonical SymPy string with real math symbols
for display (the graph title and the conversational line). The canonical string
(``DerivedFunction.equation``) is preserved untouched for the reasoning panel's
"derived by SymPy" view.
"""

from __future__ import annotations

import re

_SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def pretty_equation(equation: str) -> str:
    """``y = 2*sin(3*x - 1)`` -> ``y = 2·sin(3x − 1)``; ``(x - 1)**2`` -> ``(x − 1)²``."""
    s = re.sub(r"\*\*(\d+)", lambda m: m.group(1).translate(_SUPERSCRIPT), equation)
    s = s.replace("**", "^")  # symbolic exponents, if any
    s = re.sub(r"\*x", "x", s)  # 3*x -> 3x
    s = re.sub(r"\*\(", "(", s)  # 2*( -> 2(
    s = s.replace("*", "·")  # remaining products, e.g. 2*sin -> 2·sin
    s = s.replace("log(", "ln(")  # v1's default log is natural log
    s = s.replace(" - ", " − ").replace("(-", "(−").replace("= -", "= −")
    return s
