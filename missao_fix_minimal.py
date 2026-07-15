"""
Missao: AFP-Team corrige bugs do dashboard (versao minimalista).
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.as_posix())

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
if not registry.project_exists("AFP-Team"):
    registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

agents = {}
for aid in ("dev", "qa", "coordenador"):
    agent = registry.load_agent("AFP-Team", aid)
    agents[aid] = agent

coord = agents["coordenador"]
coord.set_subordinates({
    "dev": agents["dev"],
    "qa": agents["qa"],
})

objective = (
    "Corrigir os seguintes bugs no JavaScript de src/dashboard/index.html:\n\n"
    "1. A API /api/projects retorna project_id, project_name, agent_id (nao 'id' ou 'name' ou 'id')\n"
    "2. O JS usa project.name, project.id, agent.id — esses campos nao existem na resposta\n"
    "3. A API retorna agents[] diretamente no projeto, nao tem nested teams[]\n"
    "4. project.total_executions e project.active_agents nao existem — usar 0\n\n"
    "SOLUCAO: Normalizar a resposta da API no loadInitialData() mapeando\n"
    "project_id -> id, project_name -> name, agent_id -> id,\n"
    "e criar teams[] artificial com 1 team contendo agents[].\n"
    "Assim o resto do JS (renderProjects, renderTeams, renderTeamDetail) funciona sem rewrites.\n\n"
    "REGRAS:\n"
    "- Usar refactor_code para modificar index.html\n"
    "- Nao mexer em server.py\n"
    "- Nao mudar CSS/HTML, apenas JS\n"
    "- Apos corrigir, recarregar o navegador e verificar se os cards mostram dados reais"
)

context = "O arquivo src/dashboard/index.html tem ~1388 linhas. O server entrega /api/projects com dados reais."

print("Iniciando missao...")
sys.stdout.flush()

result = coord.execute({
    "action": "plan_and_execute",
    "goal": objective,
    "context": context,
})

print(f"Status: {result['status']}")
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}")
for s in result.get("steps", []):
    print(f"  [{s['agent_id']:10s}] {s['step']:40s} {s['status']}")
sys.stdout.flush()
