"""
Agent Factory — Agents
=======================
Módulo de agentes componentizados.
"""

from .base import AgentBase, CoordinatorAgent
from .real import SubprocessAgent, LLMAgent

__all__ = [
    "AgentBase",
    "CoordinatorAgent",
    "SubprocessAgent",
    "LLMAgent",
]
