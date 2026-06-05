"""Domain exceptions for the math core.

These map onto the output envelope's ``error`` type. They carry enough
structure for the agent to produce a useful, honest message — never a wrong
graph.
"""

from __future__ import annotations


class MathCoreError(Exception):
    """Base class for all math-core errors."""


class OutOfScopeError(MathCoreError):
    """The request is well-formed but outside v1's supported scope.

    ``reason`` is a stable machine code (e.g. ``"implicit"``, ``"polar"``,
    ``"not_a_function"``); ``message`` is the human-readable explanation.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


class DerivationError(MathCoreError):
    """The IR is structurally valid but cannot be derived into a function.

    e.g. a "quadratic" with leading coefficient 0, an inconsistent
    vertex+point pair, or a numeric field that isn't a finite real literal.
    """

    def __init__(self, message: str, reason: str = "underivable") -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
