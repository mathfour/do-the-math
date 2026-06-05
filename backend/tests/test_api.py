"""POST /chat: envelope responses end-to-end (Anthropic adapter mocked)."""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from app import main
from app.do_the_math.providers.fake import FakeProvider

client = TestClient(main.app)


@pytest.fixture
def fake_adapter(monkeypatch):
    """Replace AnthropicAdapter so /chat runs without a network call."""

    scripted: dict = {}

    def _factory(api_key, model):
        return FakeProvider(scripted)

    monkeypatch.setattr(main, "AnthropicAdapter", _factory)
    return scripted


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_missing_key_returns_error_envelope(monkeypatch):
    # Ensure no env key leaks in.
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, env_api_key=None))
    resp = client.post("/chat", json={"message": "graph a line"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "error"
    assert body["payload"]["reason"] == "missing_api_key"


def test_chat_happy_path_returns_graph(fake_adapter):
    fake_adapter.update({"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"})
    resp = client.post(
        "/chat",
        json={"message": "a parabola with vertex (1,2) opening up"},
        headers={"X-Anthropic-Key": "sk-test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "graph"
    assert body["payload"]["equation"] == "y = (x - 1)**2 + 2"


def test_llm_summaries_flag_is_honored(fake_adapter):
    fake_adapter.update({"kind": "trig", "func": "sin"})
    # Default (omitted) -> off -> deterministic written line.
    off = client.post(
        "/chat", json={"message": "sine"}, headers={"X-Anthropic-Key": "sk-test"}
    ).json()
    assert "for you" not in off["explanation"]  # FakeProvider.write_summary not called
    # Opt in -> the provider phrases it (FakeProvider returns "Here's ... for you.").
    on = client.post(
        "/chat",
        json={"message": "sine", "llm_summaries": True},
        headers={"X-Anthropic-Key": "sk-test"},
    ).json()
    assert "for you" in on["explanation"]


def test_chat_clarification_path(fake_adapter):
    fake_adapter.update({"kind": "parabola_vertex_direction", "direction": "up"})
    resp = client.post(
        "/chat",
        json={"message": "graph a parabola"},
        headers={"X-Anthropic-Key": "sk-test"},
    )
    body = resp.json()
    assert body["type"] == "clarification"
    assert body["payload"]["field"] == "vertex"


def test_empty_message_rejected_by_validation():
    resp = client.post("/chat", json={"message": ""}, headers={"X-Anthropic-Key": "sk-test"})
    assert resp.status_code == 422


def test_clarification_round_trip_completes_the_graph(monkeypatch):
    """SPEC §4 loop end-to-end: underspecified -> question -> answer -> graph.

    The adapter is rebuilt per request, so script a fresh provider response for
    each /chat call: first incomplete (no vertex), then complete.
    """
    responses = [
        {"kind": "parabola_vertex_direction", "direction": "up"},  # missing vertex
        {"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"},
    ]
    seen_history: list = []

    def _factory(api_key, model):
        provider = FakeProvider(responses.pop(0))
        # Wrap to record the history the interpreter passed through.
        original = provider.complete_intent

        def _record(message, history=None):
            seen_history.append(history)
            return original(message, history)

        provider.complete_intent = _record
        return provider

    monkeypatch.setattr(main, "AnthropicAdapter", _factory)
    headers = {"X-Anthropic-Key": "sk-test"}

    # Turn 1: underspecified -> clarification.
    first = client.post("/chat", json={"message": "graph a parabola"}, headers=headers).json()
    assert first["type"] == "clarification"
    assert first["payload"]["field"] == "vertex"

    # Turn 2: the user's answer, carried back with conversation history.
    history = [
        {"role": "user", "content": "graph a parabola"},
        {"role": "assistant", "content": first["payload"]["question"]},
    ]
    second = client.post(
        "/chat",
        json={"message": "the vertex is (1, 2)", "history": history},
        headers=headers,
    ).json()
    assert second["type"] == "graph"
    assert second["payload"]["equation"] == "y = (x - 1)**2 + 2"
    assert seen_history[-1] == history  # history reached the interpreter
