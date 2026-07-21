"""Launcher for the AFP Dashboard server."""
import sys
sys.path.insert(0, '.')
from src.registry import get_registry
from src.project_discovery import register_discovered_projects
registry = get_registry()
register_discovered_projects(registry)
from src.dashboard.server import DashboardServer
server = DashboardServer(port=8080)
server.start()
