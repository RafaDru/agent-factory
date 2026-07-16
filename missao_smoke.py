"""
Missao: AFP-Team executa smoke test do dashboard.
DEV inicia servidor em background e valida endpoints via HTTP.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
if not registry.project_exists("AFP-Team"):
    registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

agents = {}
for aid in ("dev", "qa", "coordenador"):
    agents[aid] = registry.load_agent("AFP-Team", aid)

coord = agents["coordenador"]
coord.set_subordinates({
    "dev": agents["dev"],
    "qa": agents["qa"],
})

objective = (
    "Executar smoke test do dashboard da Agent Factory.\n\n"

    "TAREFA 1 — DEV: Iniciar servidor do dashboard em BACKGROUND:\n"
    "Criar script _smoke_dash.py que:\n"
    "1. Importa DashboardServer de src.dashboard.server\n"
    "2. Cria DashboardServer(port=8080) e chama .start()\n"
    "3. Usa Start-Process (Windows) para rodar em background detached\n"
    "4. Imprime URL http://localhost:8080\n"
    "5. Aguarda 3s, faz GET /api/events?project=AFP-Team via urllib\n"
    "6. Imprime numero de eventos retornados\n"
    "7. Deixa o servidor rodando (nao parar)\n"
    "Executar o script smoke com timeout de 10s.\n\n"

    "TAREFA 2 — QA: Validar que a API responde corretamente:\n"
    "1. review_code no _smoke_dash.py\n"
    "2. Apos execucao, verificar se retornou eventos\n\n"

    "TAREFA 3 — DEV: git add + commit do _smoke_dash.py"
)

context = (
    "DashboardServer nao requer notifier (usa registry automaticamente). "
    "Porta 8080. "
    "Nao matar servidores existentes. "
    "O script deve rodar em background e nao travar a sessao."
)

print(f"Delegando smoke test... ({len(objective)} chars)", flush=True)
result = coord.execute({
    "action": "plan_and_execute",
    "goal": objective,
    "context": context,
})
print(f"Status: {result['status']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:45s} {s['agent_id']:10s} {s['status']}", flush=True)
