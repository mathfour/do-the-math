"""agents + router: registration, dispatch, and every envelope path.

Wires interpreter -> agent -> engine -> renderer through a FakeProvider, so no
network is touched.
"""

from app.do_the_math.agents import AgentRegistry, GraphingAgent, Request, graphing
from app.do_the_math.math_interpreter import MathInterpreter
from app.do_the_math.providers.fake import FakeProvider
from app.do_the_math.router import Router, build_default_registry


def _router(scripted: dict) -> Router:
    return Router(MathInterpreter(FakeProvider(scripted)), build_default_registry())


# --- Registration & dispatch ------------------------------------------------ #


def test_default_registry_has_one_agent_and_it_is_graphing():
    registry = build_default_registry()
    assert [a.name for a in registry.agents] == ["graphing"]


def test_router_dispatches_to_graphing_agent():
    registry = AgentRegistry()
    registry.register(GraphingAgent())
    agent = registry.find(
        {"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"}
    )
    assert isinstance(agent, GraphingAgent)


def test_graphing_agent_handles_kind_classification():
    agent = GraphingAgent()
    assert agent.handles_kind("linear_direct") is True
    assert agent.handles_kind("totally_unknown") is False


# --- Envelope paths through the full slice ---------------------------------- #


def test_happy_path_returns_graph_with_ir_and_equation():
    env = _router(
        {"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"}
    ).handle("p")
    assert env.type == "graph"
    assert env.payload["equation"] == "y = (x - 1)**2 + 2"
    assert env.payload["ir"]["kind"] == "parabola_vertex_direction"
    assert env.payload["figure"]["data"][0]["type"] == "scatter"


def test_underspecified_returns_clarification():
    env = _router({"kind": "parabola_vertex_direction", "direction": "up"}).handle("p")
    assert env.type == "clarification"
    assert env.payload["field"] == "vertex"


def test_help_request_returns_help_envelope():
    # "What can I graph?" is a help question, not a graph request.
    env = _router({"kind": "help"}).handle("what can I graph?")
    assert env.type == "help"
    assert env.explanation


def test_unsupported_returns_error():
    env = _router({"kind": "unsupported", "reason": "implicit", "detail": "circle"}).handle("p")
    assert env.type == "error"
    assert env.payload["reason"] == "implicit"


def test_out_of_scope_geometry_returns_error():
    env = _router({"kind": "line_two_points", "point1": [1, 0], "point2": [1, 9]}).handle("p")
    assert env.type == "error"
    assert env.payload["reason"] == "not_a_function"


def test_interpreter_failure_becomes_error_envelope():
    class Boom:
        name = "boom"

        def complete_intent(self, message, history=None):
            raise RuntimeError("model unreachable")

    router = Router(MathInterpreter(Boom()), build_default_registry())
    env = router.handle("p")
    assert env.type == "error"
    assert env.payload["reason"] == "interpreter_error"


def test_request_carries_message_and_raw_intent():
    agent = GraphingAgent()
    req = Request(message="hi", raw_intent={"kind": "trig", "func": "sin"})
    env = agent.execute(req)
    assert env.type == "graph"


def test_graph_explanation_uses_provider_summary(monkeypatch):
    monkeypatch.setattr(graphing, "LLM_SUMMARIES_ENABLED", True)
    provider = FakeProvider(
        {"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"},
        summary="Ta-da — one parabola!",
    )
    env = Router(MathInterpreter(provider), build_default_registry()).handle("p")
    assert env.type == "graph"
    assert env.explanation == "Ta-da — one parabola!"
    # The model was handed SymPy-verified facts, including the pretty equation.
    assert provider.summary_calls[0]["equation"] == "y = (x − 1)² + 2"


def test_llm_summary_disabled_uses_written_line(monkeypatch):
    monkeypatch.setattr(graphing, "LLM_SUMMARIES_ENABLED", False)
    provider = FakeProvider(
        {"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"},
        summary="SHOULD NOT BE USED",
    )
    env = Router(MathInterpreter(provider), build_default_registry()).handle("p")
    assert env.type == "graph"
    assert env.explanation != "SHOULD NOT BE USED"
    assert not provider.summary_calls  # the model was never asked to phrase


def test_graph_explanation_falls_back_without_provider():
    env = GraphingAgent().execute(
        Request(
            message="p",
            raw_intent={"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"},
            provider=None,
        )
    )
    assert env.type == "graph"
    assert "parabola" in env.explanation  # deterministic written line
    assert "y = (x − 1)²" in env.explanation


def test_graph_explanation_falls_back_when_provider_summary_errors(monkeypatch):
    monkeypatch.setattr(graphing, "LLM_SUMMARIES_ENABLED", True)

    class Boom(FakeProvider):
        def write_summary(self, facts):
            raise RuntimeError("model down")

    env = Router(
        MathInterpreter(Boom({"kind": "trig", "func": "sin"})), build_default_registry()
    ).handle("p")
    assert env.type == "graph"
    assert "sine wave" in env.explanation  # fell back to the written line
