"""
Missao B: Timestamp no Interaction Flow + SSE live update.
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
    "Duas correcoes em src/dashboard/index.html:\n\n"

    "1. TIMESTAMP no Interaction Flow:\n"
    "Em renderTimeline() (~linha 1610), cada event tem event.timestamp. "
    "Adicionar em cada .timeline-item: "
    "<div class='timeline-time'>${new Date(event.timestamp).toLocaleString()}</div> "
    "logo apos a mensagem. "
    "Adicionar CSS: .timeline-time { font-size:0.75rem; color: var(--text-secondary); margin-top:4px; }\n\n"

    "2. SSE LIVE UPDATE sem recriar DOM:\n"
    "Problema: handleAgentEvent() chama renderTeamDetail() que faz "
    "container.innerHTML = ... recriando todo o DOM a cada evento SSE. "
    "Isso causa flickering e perde estado.\n\n"
    "Corrigir:\n"
    "  a) Em handleAgentEvent() (~linha 1290), substituir: "
    "se card existir (document.getElementById('agent-'+agentId)), "
    "atualizar SELETIVAMENTE em vez de recriar:\n"
    "     - .agent-status: atualizar classe + texto (IDLE/SUCCESS/FAILED/RUNNING)\n"
    "     - .status-dot: atualizar classe (dot-idle/dot-success/dot-failed/dot-running)\n"
    "     - .task-name: atualizar texto\n"
    "     - .mission-name: atualizar texto\n"
    "     - .agent-card: atualizar classe (running/success/failed/ready)\n"
    "     - timer: criar ou atualizar\n"
    "  b) Se card NAO existir, chamar renderTeamDetail() (primeira carga)\n"
    "  c) Nas atualizacoes, usar element.textContent = ... em vez de innerHTML\n"
    "  d) Nao mexer no LLM select, context bar, last-model\n\n"
    "Dica: criar funcao auxiliar updateAgentCardUI(agentId) que faz as alteracoes "
    "seletivas, chamada por handleAgentEvent.\n\n"

    "Commits apos cada passo. QA revisa. pytest tests/ -v."
)

print(f"Delegando Missao B... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
