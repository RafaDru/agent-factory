"""
Missao v4: corrigir 5 issues do board (#7 a #11).
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
    "Executar 5 correcoes em src/dashboard/index.html na ordem abaixo.\n"
    "ANTES de cada refactor_code, usar read_file para ler o estado atual do arquivo.\n"
    "APOS cada alteracao, git add + git commit.\n"
    "QA revisa cada passo. pytest tests/ -v no final.\n"
    "ATUALIZAR dev/CONTEXTO.md com licoes aprendidas.\n\n"

    "--- ISSUE #11: Design clean (remover bordas dos cards) ---\n"
    "No CSS, encontrar '.agent-card {' e '.mission-card {' e:\n"
    "  - Remover 'border: 1px solid var(--border-glass);' de ambos\n"
    "  - Adicionar 'box-shadow: 0 2px 8px rgba(0,0,0,0.06);' no lugar\n"
    "  - Manter border-radius\n\n"

    "--- ISSUE #7: Espacamento entre secoes ---\n"
    "1. Encontrar '.team-detail-layout { gap: 24px; }' "
    "e garantir que gap:24px esta aplicado.\n"
    "2. Encontrar '.last-execution-section {' e adicionar "
    "'margin-bottom: 24px;' se nao existir.\n"
    "3. Encontrar '.agents-grid {' e adicionar "
    "'margin-bottom: 16px;' se nao existir.\n\n"

    "--- ISSUE #9: Modelo LLM nunca aparece ---\n"
    "Problema: handleAgentEvent() extrai model de event.metrics.model, "
    "mas eventos sem metrics nunca populam lastExecution.model.\n"
    "Corrigir em handleAgentEvent (~linha 1260):\n"
    "  Na secao onde extrai model, adicionar fallback:\n"
    "    const model = event.metrics?.model \n"
    "      || (event.metrics?.provider ? `${event.metrics.provider}/${event.metrics.model || ''}` : null)\n"
    "      || (event.payload?.model)\n"
    "      || (agentState.llmConfig?.provider)\n"
    "      || null;\n"
    "  E guardar no agentState: agentState.llmConfig = { provider: event.metrics?.provider || null };\n\n"

    "--- ISSUE #10: Separar Status Atual do Status da Ultima Tarefa ---\n"
    "No card do agente, atualmente o badge mostra o ULTIMO status recebido via SSE.\n"
    "Deseja-se DOIS indicadores:\n"
    "  1. Status ATUAL (circulo + texto: IDLE | RUNNING) - fica onde esta\n"
    "  2. Ultima TAREFA (badge separado: SUCCESS | FAILED | - ) - novo elemento\n"
    "Em renderTeamDetail: apos o status atual, adicionar:\n"
    "  <div class='last-task-badge ${lastStatusClass}'>Ultima: ${lastLabel}</div>\n"
    "Onde lastStatusClass/lastLabel vem de getStatusInfo(agentState.lastTaskStatus).\n"
    "agentState.lastTaskStatus e atualizado em handleAgentEvent quando "
    "event.status for 'completed' ou 'failed'.\n"
    "CSS para .last-task-badge: font-size 0.7rem, padding 2px 8px, border-radius, opacity 0.8.\n\n"

    "--- ISSUE #8: Interaction Flow como conversa/flowchart ---\n"
    "Substituir renderTimeline() para formato de CONVERSA (como chat):\n"
    "  - Cada mission-card vira uma 'conversa' com baloes\n"
    "  - Cada passo: avatar do agente + mensagem + timestamp\n"
    "  - Remover setas (→), usar indentacao por nivel\n"
    "  - Alternar alinhamento: agente A left, agente B right (como chat)\n"
    "  - Agrupar por task_id (ja existe o grouping)\n"
    "  - Se task_id vazio, mostrar como 'Uncategorized'\n"
    "  - CSS .mission-card: sem borda, com sombra sutil, padding 16px, margin-bottom 16px\n"
    "  - .mission-step: display flex, align-items center, gap 8px, sem bg, sem borda\n"
    "  - Usar emoji do agente no avatar\n\n"

    "REGRAS:\n"
    "- read_file antes de cada refactor_code\n"
    "- git add + git commit apos cada alteracao\n"
    "- QA revisa cada passo\n"
    "- pytest tests/ -v no final\n"
    "- Atualizar dev/CONTEXTO.md com licoes"
)

print(f"Missao v4: 5 issues...", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
