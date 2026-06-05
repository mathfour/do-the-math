"""A scripted provider for tests — no network, fully deterministic.

Feed it the raw IR dict(s) you want it to "produce" so interpreter -> agent ->
engine -> renderer wiring can be exercised without a live model.
"""

from __future__ import annotations


class FakeProvider:
    """Returns pre-scripted IR dicts, ignoring the actual message text."""

    name = "fake"

    def __init__(self, scripted: dict | list[dict], summary: str | None = None):
        self._queue: list[dict] = [scripted] if isinstance(scripted, dict) else list(scripted)
        self._summary = summary
        self.calls: list[tuple[str, list[dict] | None]] = []
        self.summary_calls: list[dict] = []

    def complete_intent(self, message: str, history: list[dict] | None = None) -> dict:
        self.calls.append((message, history))
        if not self._queue:
            raise AssertionError("FakeProvider ran out of scripted responses.")
        # Last item repeats once exhausted-but-present (convenient for reuse).
        return self._queue.pop(0) if len(self._queue) > 1 else self._queue[0]

    def write_summary(self, facts: dict) -> str:
        self.summary_calls.append(facts)
        if self._summary is not None:
            return self._summary
        return f"Here's {facts.get('equation', 'your graph')} for you."
