"""
Missao final: corrigir todos os pontos pendentes + atualizar contextos.
Delegacao EXCLUSIVA via AFP-Team, sem edicao direta.
"""
import sys
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
registry = get_registry()
agents = {}
for aid in ("dev", "qa"):
    agents[aid] = registry.load_agent("AFP-Team", aid)
coord = agents["dev"]  # Usar dev diretamente, sem coordinator que inclui designer

objective = (
    "Corrigir 5 problemas em src/dashboard/index.html:\n\n"

    "1. CSS DUPLICADO — Interaction Flow com setas sobrepostas e cores fixas:\n"
    "No final do bloco <style>, ha DOIS conjuntos de regras para "
    ".mission-card, .mission-step, .mission-arrow. "
    "O SEGUNDO conjunto (comentario 'Added styles for...') usa cores fixas "
    "(#ccc, #f9f9f9, #e0e0e0) que SOBRESCREVEM o primeiro conjunto "
    "(que usa variaveis CSS themed)."
    "REMOVER o segundo conjunto inteiro e ajustar o primeiro:\n"
    "  - .mission-steps { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }\n"
    "  - .mission-step { ... } (manter o primeiro, themed)\n"
    "  - .mission-arrow { color:var(--cyan); font-weight:bold; font-size:1.2rem; margin:0 4px; flex-shrink:0; }\n\n"

    "2. PORTUGUES RESIDUAL (i18n):\n"
    "Substituir strings hardcoded em portugues:\n"
    "  a) 'agentes' → L.agents (ja existe no objeto L)\n"
    "  b) 'Executing...' → L.executing (ADICIONAR ao objeto L)\n"
    "  c) 'Mission:' → L.mission (ADICIONAR ao objeto L)\n"
    "  d) 'Uncategorized' → L.uncategorized (ADICIONAR ao objeto L)\n\n"

    "3. TIMESTAMP ja existe no Interaction Flow (verificar se esta funcionando).\n\n"

    "4. SSE LIVE UPDATE:\n"
    "handleAgentEvent() chama renderTeamDetail() que recria TODO o DOM "
    "a cada evento SSE. Isso causa flickering.\n"
    "Em handleAgentEvent (~linha 1205), substituir:\n"
    "  if (state.currentView === 'team-detail') { renderTeamDetail(); }\n"
    "por:\n"
    "  if (state.currentView === 'team-detail') {\n"
    "    const card = document.getElementById('agent-'+agentId);\n"
    "    if (card) { updateAgentCardUI(agentId); }\n"
    "    else { renderTeamDetail(); }\n"
    "  }\n"
    "Criar funcao updateAgentCardUI(agentId) que atualiza SELETIVAMENTE:\n"
    "  - card.className = 'agent-card ' + info.cardClass\n"
    "  - .agent-status: className + innerHTML (status-dot + label)\n"
    "  - .task-name: textContent\n"
    "  - .mission-name: textContent\n"
    "  - timer: criar/remover div.timer conforme status\n\n"

    "5. ATUALIZAR CONTEXTOS DOS AGENTES:\n"
    "Adicionar em contexts/AFP-Team/dev/CONTEXTO.md e "
    "contexts/AFP-Team/qa/CONTEXTO.md a licao:\n"
    "'NUNCA criar CSS duplicado. Sempre verificar se a regra ja existe "
    "antes de adicionar novas. Manter consistencia com variaveis CSS do tema.'\n\n"

    "Ordem: 1 (CSS) → 2 (i18n) → 4 (SSE) → 5 (contextos) → pytest.\n"
    "Commits apos cada passo."
)

coord2 = registry.load_agent("AFP-Team", "coordenador")
coord2.set_subordinates({"dev": agents["dev"], "qa": agents["qa"]})

print(f"Delegando missao final... ({len(objective)} chars)", flush=True)
result = coord2.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
