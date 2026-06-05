"""Provider adapter layer. Anthropic is the only implemented adapter in v1.

The interface is designed so OpenAI / Azure / Gemini are pure additions later —
a new adapter implementing ``ProviderAdapter``, nothing else changes.
"""

from .base import ProviderAdapter
from .fake import FakeProvider

__all__ = ["ProviderAdapter", "FakeProvider"]
