import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

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

print("Gerando plano...")
sys.stdout.flush()
t0 = time.time()
tasks_with_meta = coord._plan_with_llm(objective, context)
print(f"Plano gerado em {time.time()-t0:.1f}s: {len(tasks_with_meta)} tasks")
for t in tasks_with_meta:
    print(f"  {t.get('name','?'):30s} -> {t.get('agent_id','?')}")
sys.stdout.flush()

# Simular o que _plan_and_execute faz manualmente
tasks = [t.get("task", t) for t in tasks_with_meta]
for i, step in enumerate(tasks_with_meta):
    agent_id = step.get("agent_id", "")
    subtask = step.get("task", {})
    step_name = step.get("name", f"step-{i}")
    
    print(f"\n[{i+1}/{len(tasks_with_meta)}] Executando {step_name} -> {agent_id}...")
    sys.stdout.flush()
    
    t1 = time.time()
    try:
        result = agents[agent_id].run(subtask)
        elapsed = time.time() - t1
        print(f"  Concluido em {elapsed:.1f}s: {result.status}")
        if hasattr(result, 'summary'):
            print(f"  Summary: {str(result.summary)[:200]}")
        sys.stdout.flush()
    except Exception as e:
        elapsed = time.time() - t1
        print(f"  ERRO apos {elapsed:.1f}s: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        break
