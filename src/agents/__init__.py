"""
Agent Factory — Agents
=======================
Módulo de agentes componentizados.
"""

from .base import AgentBase, CoordinatorAgent
from .real import SubprocessAgent, LLMAgent
from .factory_dev import AgentFactoryDevAgent
from .qa import QAAgent
from .coordinator import AgentFactoryCoordinator

__all__ = [
    "AgentBase",
    "CoordinatorAgent",
    "SubprocessAgent",
    "LLMAgent",
    "AgentFactoryDevAgent",
    "QAAgent",
    "AgentFactoryCoordinator",
]
