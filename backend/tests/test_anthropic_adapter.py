"""Anthropic adapter: maps a tool-use response to the raw IR dict (network mocked)."""

from types import SimpleNamespace

import pytest

from app.do_the_math.providers import anthropic_adapter
from app.do_the_math.providers.anthropic_adapter import AnthropicAdapter


class _FakeMessages:
    def __init__(self, response):
        self._response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class _FakeClient:
    def __init__(self, response):
        self.messages = _FakeMessages(response)


def _install_fake(monkeypatch, blocks):
    response = SimpleNamespace(content=blocks)
    fake = _FakeClient(response)
    monkeypatch.setattr(anthropic_adapter.anthropic, "Anthropic", lambda api_key: fake)
    return fake


def test_extracts_intent_from_tool_use(monkeypatch):
    block = SimpleNamespace(
        type="tool_use",
        name="submit_math_intent",
        input={"intent": {"kind": "linear_direct", "slope": 2, "intercept": 1}},
    )
    fake = _install_fake(monkeypatch, [block])

    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    raw = adapter.complete_intent("a line")

    assert raw == {"kind": "linear_direct", "slope": 2, "intercept": 1}
    # Forced tool choice + correct model were sent.
    kwargs = fake.messages.last_kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["tool_choice"] == {"type": "tool", "name": "submit_math_intent"}
    assert kwargs["messages"][-1] == {"role": "user", "content": "a line"}


def test_tolerates_flat_intent_without_wrapper(monkeypatch):
    block = SimpleNamespace(
        type="tool_use", name="submit_math_intent", input={"kind": "trig", "func": "sin"}
    )
    _install_fake(monkeypatch, [block])
    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    assert adapter.complete_intent("sine") == {"kind": "trig", "func": "sin"}


def test_recovers_intent_serialized_as_json_string(monkeypatch):
    # The model sometimes serializes the intent object to a JSON string.
    block = SimpleNamespace(
        type="tool_use",
        name="submit_math_intent",
        input={"intent": '{"kind": "linear_direct", "slope": 2, "intercept": 1}'},
    )
    _install_fake(monkeypatch, [block])
    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    assert adapter.complete_intent("a line") == {
        "kind": "linear_direct",
        "slope": 2,
        "intercept": 1,
    }


def test_non_json_string_intent_raises(monkeypatch):
    block = SimpleNamespace(
        type="tool_use", name="submit_math_intent", input={"intent": "parabola"}
    )
    _install_fake(monkeypatch, [block])
    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    with pytest.raises(RuntimeError):
        adapter.complete_intent("?")


def test_history_is_prepended(monkeypatch):
    block = SimpleNamespace(
        type="tool_use", name="submit_math_intent", input={"kind": "trig", "func": "cos"}
    )
    fake = _install_fake(monkeypatch, [block])
    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    history = [{"role": "user", "content": "earlier"}]
    adapter.complete_intent("now", history=history)
    assert fake.messages.last_kwargs["messages"][0] == {"role": "user", "content": "earlier"}


def test_missing_tool_call_raises(monkeypatch):
    block = SimpleNamespace(type="text", text="I cannot help")
    _install_fake(monkeypatch, [block])
    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    with pytest.raises(RuntimeError):
        adapter.complete_intent("?")


def test_empty_api_key_rejected():
    with pytest.raises(ValueError):
        AnthropicAdapter(api_key="", model="claude-sonnet-4-6")


def test_write_summary_returns_model_text(monkeypatch):
    block = SimpleNamespace(type="text", text="  Here's your parabola!  ")
    _install_fake(monkeypatch, [block])
    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    out = adapter.write_summary({"shape": "parabola", "equation": "y = x²", "details": "opens up"})
    assert out == "Here's your parabola!"  # trimmed


def test_write_summary_empty_response_raises(monkeypatch):
    block = SimpleNamespace(type="text", text="   ")
    _install_fake(monkeypatch, [block])
    adapter = AnthropicAdapter(api_key="sk-test", model="claude-sonnet-4-6")
    with pytest.raises(RuntimeError):
        adapter.write_summary({"shape": "line", "equation": "y = x", "details": ""})
