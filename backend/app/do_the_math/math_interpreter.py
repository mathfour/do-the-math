"""English -> raw Math Intent dict. Thin wrapper over a provider adapter.

The interpreter owns *no* math and *no* provider specifics — it just delegates
to whichever ``ProviderAdapter`` it was given. This is the seam future agents
reuse, and the seam tests mock (via ``FakeProvider``).
"""

from __future__ import annotations

from .providers.base import ProviderAdapter


class MathInterpreter:
    def __init__(self, provider: ProviderAdapter):
        self.provider = provider

    def to_raw_intent(self, message: str, history: list[dict] | None = None) -> dict:
        """Return the raw IR dict the provider produced for ``message``."""
        return self.provider.complete_intent(message, history)
