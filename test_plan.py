import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
if not registry.project_exists("AFP-Team"):
    registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

coord = registry.load_agent("AFP-Team", "coordenador")

objective = (
    "Corrigir os seguintes bugs no JavaScript de src/dashboard/index.html:\n\n"
    "1. A API /api/projects retorna project_id, project_name, agent_id (nao 'id' ou 'name')\n"
    "2. O JS usa project.name, project.id, agent.id — esses campos nao existem na resposta\n"
    "3. A API retorna agents[] diretamente no projeto, nao tem nested teams[]\n"
    "4. project.total_executions e project.active_agents nao existem\n\n"
    "SOLUCAO: Normalizar a resposta da API no loadInitialData() mapeando "
    "project_id -> id, project_name -> name, agent_id -> id.\n"
    "REGRAS: Usar refactor_code. Nao mexer em server.py. Nao mudar CSS/HTML, apenas JS."
)

context = "O arquivo src/dashboard/index.html tem ~1388 linhas."

print(f"Testing _plan_with_llm with {len(objective)} chars...")
sys.stdout.flush()
t0 = time.time()

try:
    tasks = coord._plan_with_llm(objective, context)
    print(f"Plan generated in {time.time()-t0:.1f}s: {len(tasks)} tasks")
    for t in tasks:
        print(f"  {t.get('name','?'):30s} -> {t.get('agent_id','?')}")
    sys.stdout.flush()
except Exception as e:
    print(f"ERROR in _plan_with_llm: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
