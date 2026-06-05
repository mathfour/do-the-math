"""The Agent interface and registry.

Future agents (Solver, Proof, ...) implement ``Agent`` and register themselves;
the router dispatches by asking each ``can_handle(raw_intent)``. No agent is
special-cased in the orchestrator — adding one is a registration, not a router
edit. v1 registers exactly one agent (GraphingAgent).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..ir import Envelope
from ..providers.base import ProviderAdapter


@dataclass(frozen=True)
class Request:
    """What an agent needs to execute: the message, the raw IR, history, and the
    provider (so an agent can ask the model to phrase its result)."""

    message: str
    raw_intent: dict
    history: list[dict] | None = None
    provider: ProviderAdapter | None = None
    use_llm_summary: bool = False


@runtime_checkable
class Agent(Protocol):
    name: str

    def can_handle(self, raw_intent: dict) -> bool:
        """Whether this agent claims the request, classified by its IR kind."""
        ...

    def execute(self, request: Request) -> Envelope:
        """Produce the output envelope for a claimed request."""
        ...


class AgentRegistry:
    """Ordered registry; the first agent that ``can_handle`` a request wins."""

    def __init__(self) -> None:
        self._agents: list[Agent] = []

    def register(self, agent: Agent) -> None:
        self._agents.append(agent)

    @property
    def agents(self) -> list[Agent]:
        return list(self._agents)

    def find(self, raw_intent: dict) -> Agent | None:
        for agent in self._agents:
            if agent.can_handle(raw_intent):
                return agent
        return None
