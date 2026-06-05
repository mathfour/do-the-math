"""Router / classifier — dispatches a message to the right agent.

v1 is deliberately simple: interpret the message into a raw IR, then ask the
registry which agent claims it. The mechanism (interpret -> classify -> dispatch)
is the real one future agents plug into; only the registry's contents grow.
"""

from __future__ import annotations

from .agents.base import AgentRegistry, Request
from .agents.graphing import GraphingAgent
from .ir import Envelope
from .math_interpreter import MathInterpreter


class Router:
    def __init__(self, interpreter: MathInterpreter, registry: AgentRegistry):
        self.interpreter = interpreter
        self.registry = registry

    def handle(self, message: str, history: list[dict] | None = None) -> Envelope:
        try:
            raw_intent = self.interpreter.to_raw_intent(message, history)
        except Exception as exc:  # provider/transport failure — never crash the app
            return Envelope.error(
                f"Couldn't reach the language model to interpret that request: {exc}",
                reason="interpreter_error",
            )

        agent = self.registry.find(raw_intent)
        if agent is None:
            return Envelope.error(
                "No agent can handle that kind of request yet.", reason="no_agent"
            )
        return agent.execute(Request(message=message, raw_intent=raw_intent, history=history))


def build_default_registry() -> AgentRegistry:
    """The v1 registry: exactly one agent registered."""
    registry = AgentRegistry()
    registry.register(GraphingAgent())
    return registry
