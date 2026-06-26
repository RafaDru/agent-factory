"""Start Agent Factory dashboard server."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.protocols.events import EventNotifier
from src.dashboard.server import DashboardServer
from src.persistence import ContextStore

notifier = EventNotifier("pta", output_dir=".agent-factory/events")
store = ContextStore("pta")
server = DashboardServer(notifier, port=8080, context_store=store)
server.start()

print(f"Dashboard rodando em http://localhost:8080?project=pta")
print(f"Eventos (JSONL): {len(notifier.get_events())}")
print(f"Contexto SQLite: {store.get_stats()}")

while True:
    time.sleep(1)
