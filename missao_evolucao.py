"""
Missao: coordinator usa run_command para interagir com GitHub Issues.
"""
import sys
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
registry = get_registry()
agents = {}
for aid in ("dev", "qa"):
    agents[aid] = registry.load_agent("AFP-Team", aid)
coord = registry.load_agent("AFP-Team", "coordenador")
coord.set_subordinates(agents)

objective = (
    "Usar o novo run_command (comando 'gh') para gerenciar backlog via GitHub Issues.\n\n"

    "PASSO 1: Ler todas as issues abertas\n"
    "Delegar para dev: run_command com command='gh' e args=['issue','list','--repo','RafaDru/agent-factory','--state','open','--json','title,number,labels']\n"
    "Interpretar o JSON resultante.\n\n"

    "PASSO 2: Atualizar o board #4\n"
    "Para cada issue aberta, delegar para dev com:\n"
    "  run_command: command='gh', args=['project','item-add','4','--owner','@me','--url',f'https://github.com/RafaDru/agent-factory/issues/{NUMBER}']\n\n"

    "PASSO 3: Selecionar a proxima tarefa\n"
    "Priorizar por label: priority-high > bug > enhancement > infra\n"
    "Entre as issues abertas:\n"
    "  #6 - Curador: metricas de eficiencia (infra, medium)\n"
    "  #4 - GitHub Project (infra)\n"
    "A #6 e a mais importante pois permite medir a efetividade da Context Tree.\n\n"

    "PASSO 4: Planejar e executar a #6\n"
    "Criar endpoint /api/context/stats no server.py que retorna:\n"
    "  project_id, agent_id, index_bytes, total_bytes, domains, domain_count\n"
    "Usar ContextTree.stats() de src/sdk/context_tree.py.\n"
    "Arquivo: src/dashboard/server.py\n"
    "Adicionar rota em do_GET: '/api/context/stats' -> _serve_context_stats()\n"
    "Metodo _serve_context_stats(): para cada notifier, carregar ContextTree e chamar stats().\n\n"

    "PASSO 5: Atualizar contexto do coordinator\n"
    "Adicionar licao em contexts/AFP-Team/coordenador/CONTEXTO.md:\n"
    "'run_command com whitelist permite interagir com GitHub CLI (gh). "
    "Usar para ler issues, atualizar board, e gerenciar backlog.'\n\n"

    "PASSO 6: Mover issue #6 para 'In Progress' no board\n"
    "Delegar dev: run_command gh project item-edit\n\n"

    "Commits apos server.py. pytest tests/ -v."
)

print(f"Evoluindo backlog via run_command...", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
