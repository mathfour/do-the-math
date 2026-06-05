"""clarification: deterministic required-field check (no LLM)."""

from app.do_the_math.clarification import check_required


def test_complete_intent_needs_no_clarification():
    assert (
        check_required({"kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up"})
        is None
    )


def test_missing_vertex_asks_for_vertex():
    c = check_required({"kind": "parabola_vertex_direction", "direction": "up"})
    assert c is not None
    assert c.field == "vertex"
    assert "vertex" in c.question.lower()


def test_returns_first_missing_field_only():
    c = check_required({"kind": "parabola_vertex_direction"})
    assert c.field == "vertex"  # first in REQUIRED order, not "direction"


def test_unknown_kind_asks_what_to_graph():
    c = check_required({"kind": "frobnicate"})
    assert c.field == "kind"


def test_missing_kind_asks_what_to_graph():
    c = check_required({})
    assert c.field == "kind"


def test_empty_list_field_counts_as_missing():
    c = check_required({"kind": "parabola_three_points", "points": []})
    assert c.field == "points"


def test_optional_fields_do_not_trigger_clarification():
    # trig only requires func; amplitude/frequency/etc. are optional.
    assert check_required({"kind": "trig", "func": "sin"}) is None
