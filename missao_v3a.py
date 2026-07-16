"""
Missao A: i18n + timestamp no Interaction Flow.
Step 1 (gap) ja foi commitado.
"""
import sys
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
registry = get_registry()
agents = {}
for aid in ("dev", "qa", "coordenador"):
    agents[aid] = registry.load_agent("AFP-Team", aid)
coord = agents["coordenador"]
coord.set_subordinates({"dev": agents["dev"], "qa": agents["qa"]})

objective = (
    "Duas melhorias em src/dashboard/index.html:\n\n"

    "A — INTERNACIONALIZACAO (i18n):\n"
    "- Criar objeto global L no inicio do <script> com TODAS as strings fixas "
    "da interface em INGLES.\n"
    "- Substituir textos hardcoded nos templates JS por L.chave.\n"
    "- Mapeamento obrigatorio:\n"
    "   'Back' (ja ingles, manter)\n"
    "   'Refresh' (ja ingles, manter)\n"
    "   'Logs' (ja ingles, manter)\n"
    "   'AGENTS' (ja ingles, manter)\n"
    "   'ACTIVE' (ja ingles, manter)\n"
    "   'agents running' (ja ingles, manter)\n"
    "   'Agent' (ja ingles, manter)\n"
    "   'IDLE'/'SUCCESS'/'FAILED'/'RUNNING' (ja ingles, manter)\n"
    "   'No active task' (ja ingles, manter)\n"
    "   'LLM:' (ja ingles, manter)\n"
    "   'Interaction Flow' (ja ingles, manter)\n"
    "   'No interactions yet' (ja ingles, manter)\n"
    "   'Timeline' (ja ingles, manter)\n"
    "   'Event Logs' (ja ingles, manter)\n"
    "   'All Agents' (ja ingles, manter)\n"
    "   'All Types' (ja ingles, manter)\n"
    "   'Close' (ja ingles, manter)\n"
    "   'Clear' (ja ingles, manter)\n"
    "   'Projetos' -> 'Projects'\n"
    "   'Ultima Execucao' -> 'Last Execution'\n"
    "   'Nenhuma execucao recente' -> 'No recent executions'\n"
    "   'Nenhuma execucao ainda' -> 'No executions yet'\n"
    "   'Ultimo:' -> 'Last:'\n"
    "   'Filtrado:' -> 'Filtered by:'\n"
    "   'Nenhum agente' -> 'No agents'\n\n"
    "IMPORTANTE: Nao traduzir nomes de agentes/roles/projetos/dados. "
    "Só LABELS FIXOS da interface.\n\n"

    "B — TIMESTAMP no Interaction Flow:\n"
    "- renderTimeline() ja renderiza .timeline-item com nome e mensagem.\n"
    "- Cada event tem event.timestamp.\n"
    "- Adicionar em cada .timeline-item: "
    "<div class='timeline-time'>${new Date(event.timestamp).toLocaleString()}</div>\n"
    "- Adicionar no CSS .timeline-time { font-size:0.75rem; color: var(--text-secondary); margin-top:4px; }\n\n"

    "Commits apos cada passo. QA revisa cada passo. pytest tests/ -v no final."
)

print(f"Delegando Missao A... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:45s} {s['agent_id']:12s} {s['status']}", flush=True)
