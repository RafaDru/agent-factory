import sys, time, threading
sys.path.insert(0, '.')
from src.dashboard.server import DashboardHandler, DashboardServer
from src.protocols.events import EventNotifier
from src.protocols.schema import AgentEvent, AgentStatus, AgentRole
from src.agents.base import AgentBase, AgentRole as Role
from http.server import HTTPServer

# Setup
notifier = EventNotifier('demo')
DashboardHandler.notifier = notifier

server = HTTPServer(('localhost', 8080), DashboardHandler)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
print('Dashboard rodando em http://localhost:8080')

# Create agents
class Buscador(AgentBase):
    def __init__(self):
        super().__init__('buscador', 'demo', notifier, Role.WORKER)
    def validate_input(self, task):
        return True
    def execute(self, task):
        time.sleep(2)
        return {'dados': 42}

class Processador(AgentBase):
    def __init__(self):
        super().__init__('processador', 'demo', notifier, Role.WORKER)
    def validate_input(self, task):
        return True
    def execute(self, task):
        time.sleep(3)
        return {'processado': True}

# Run
b = Buscador()
p = Processador()

print('Executando Buscador...')
b.run({'task_id': 'buscar-1'})
time.sleep(1)

print('Executando Processador...')
p.run({'task_id': 'processar-1'})
time.sleep(1)

notifier.emit(AgentEvent(
    agent_id='sistema',
    agent_role='coordinator',
    status=AgentStatus.COMPLETED,
    task_id='pipeline-1',
    project_id='demo',
    message='Pipeline concluido!'
))

print('Concluido! Verifique o dashboard.')
print('Pressione Ctrl+C para encerrar.')

# Keep running
while True:
    time.sleep(1)
