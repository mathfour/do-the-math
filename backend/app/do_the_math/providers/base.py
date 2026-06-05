"""The provider adapter interface.

An adapter's one job: turn an English message into the **raw IR dict** the model
produced (the tool-call arguments). It does NOT validate or derive — that's the
math core's job. Keeping this surface tiny is what makes new providers cheap.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProviderAdapter(Protocol):
    """Maps English -> a raw Math Intent dict via some LLM provider."""

    name: str

    def complete_intent(self, message: str, history: list[dict] | None = None) -> dict:
        """Return the raw IR dict (``{"kind": ..., ...}``) for ``message``.

        ``history`` is an optional list of prior ``{role, content}`` turns used
        to complete a clarification (Phase 1 resolves only the active request).
        """
        ...
