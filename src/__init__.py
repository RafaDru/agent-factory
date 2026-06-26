"""Agent Factory — Framework reutilizável para orquestração de agentes com segregação de projetos."""

__version__ = "0.2.0"

from .protocols.schema import (
    AgentEvent,
    AgentStatus,
    AgentRole,
    TaskResult,
    ProjectConfig,
    OrchestratorState,
)
from .protocols.events import EventNotifier
from .agents.base import AgentBase, CoordinatorAgent
from .loader import AgentLoader, AgentReference, get_loader
from .orchestrator.graph import OrchestratorGraph
from .dashboard.server import DashboardServer
from .notifications.windows import send_windows_notification

__all__ = [
    "AgentEvent",
    "AgentStatus",
    "AgentRole",
    "TaskResult",
    "ProjectConfig",
    "OrchestratorState",
    "EventNotifier",
    "AgentBase",
    "CoordinatorAgent",
    "AgentLoader",
    "AgentReference",
    "get_loader",
    "OrchestratorGraph",
    "DashboardServer",
    "send_windows_notification",
]
