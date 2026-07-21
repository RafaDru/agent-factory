"""
Agent Factory — Agents
=======================
Módulo de agentes componentizados.
"""

from .base import AgentBase, CoordinatorAgent
from .real import SubprocessAgent, LLMAgent
from .coordinator import AgentFactoryCoordinator
from .worker import DeclarativeWorker

__all__ = [
    "AgentBase",
    "CoordinatorAgent",
    "SubprocessAgent",
    "LLMAgent",
    "AgentFactoryCoordinator",
    "DeclarativeWorker",
]
