import sys; sys.path.insert(0, '.')
from src.dashboard.server import DashboardServer
DashboardServer(port=8080).start()
