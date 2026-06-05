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
