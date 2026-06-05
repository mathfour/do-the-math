"""ir: discriminated-union parsing and the output envelope."""

import pytest
from pydantic import ValidationError

from app.do_the_math.ir import Envelope, IntentWrapper, ParabolaVertexDirection


def test_discriminator_selects_correct_model():
    intent = IntentWrapper(
        intent={"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"}
    ).intent
    assert isinstance(intent, ParabolaVertexDirection)
    assert intent.vertex == (1, 2)


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        IntentWrapper(intent={"kind": "linear_direct", "slope": 1, "intercept": 0, "bogus": 9})


def test_unknown_kind_rejected_by_discriminator():
    with pytest.raises(ValidationError):
        IntentWrapper(intent={"kind": "nope"})


def test_envelope_graph_constructor():
    env = Envelope.graph({"data": []}, "y = x", ir={"kind": "linear_direct"}, explanation="ok")
    assert env.type == "graph"
    assert env.payload["equation"] == "y = x"
    assert env.payload["ir"]["kind"] == "linear_direct"


def test_envelope_clarification_constructor():
    env = Envelope.clarification("Where is the vertex?", "vertex")
    assert env.type == "clarification"
    assert env.payload == {"question": "Where is the vertex?", "field": "vertex"}


def test_envelope_error_constructor():
    env = Envelope.error("nope", reason="implicit")
    assert env.type == "error"
    assert env.payload["reason"] == "implicit"
