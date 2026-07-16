"""
Resolver as 3 pendencias: Uncategorized, modelo LLM, idle event.
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
    "Resolver 3 pendencias. read_file antes de cada alteracao. "
    "git add + git commit apos cada passo. pytest tests/ -v.\n\n"

    "--- PENDENCIA 1: Uncategorized no Interaction Flow ---\n"
    "Arquivo: src/dashboard/index.html\n"
    "Causa: agentState.events sao populados em handleAgentEvent() e switchView() "
    "sem incluir task_id do evento original. renderTimeline() tenta agrupar por "
    "task_id, mas como o campo nao existe, cai em L.uncategorized.\n"
    "Corrigir em 2 lugares:\n"
    "  1. handleAgentEvent(): no .unshift() do agentState.events, adicionar:\n"
    "     taskId: event.task_id || event.trace_id || null,\n"
    "  2. switchView() (~linha 1169): no .unshift() do agentState.events, adicionar:\n"
    "     taskId: event.task_id || event.trace_id || null,\n"
    "  3. renderTimeline(): alterar o agrupamento de:\n"
    "     const key = event.task_id || event.trace_id || L.uncategorized;\n"
    "     para:\n"
    "     const key = event.taskId || event.task_id || event.trace_id || new Date(event.timestamp).toLocaleDateString();\n\n"

    "--- PENDENCIA 2: Modelo LLM nas metrics dos eventos ---\n"
    "Arquivo: src/sdk/base.py\n"
    "No metodo emit() (~linha 136), as metrics so incluem duration_ms. "
    "Adicionar provider e model do self._llm:\n"
    "Adicionar no topo do metodo, antes de criar event:\n"
    "  provider_name = getattr(self._llm, 'provider_name', None) or getattr(self._llm, '_provider_name', None)\n"
    "  model_name = getattr(self._llm, 'model_name', None) or getattr(self._llm, '_model_name', None)\n"
    "Depois em metrics:\n"
    "  metrics['provider'] = provider_name or 'unknown'\n"
    "  metrics['model'] = model_name or 'unknown'\n"
    "Importante: verificar se self._llm nao e None antes de acessar atributos.\n\n"

    "--- PENDENCIA 3: Status voltar a IDLE apos completed ---\n"
    "Arquivo: src/dashboard/index.html\n"
    "Em handleAgentEvent(), quando event.status for 'completed' ou 'success', "
    "adicionar um setTimeout para resetar o status para 'ready' apos 5 segundos:\n"
    "  if (event.status === 'completed' || event.status === 'success') {\n"
    "    if (state._idleTimers && state._idleTimers[agentId]) clearTimeout(state._idleTimers[agentId]);\n"
    "    if (!state._idleTimers) state._idleTimers = {};\n"
    "    state._idleTimers[agentId] = setTimeout(() => {\n"
    "      if (state.agentsState[agentId]) {\n"
    "        state.agentsState[agentId].status = 'ready';\n"
    "        const card = document.getElementById('agent-' + agentId);\n"
    "        if (card) updateAgentCardUI(agentId);\n"
    "      }\n"
    "    }, 5000);\n"
    "  }\n\n"

    "Ordem: 2 (base.py) -> 1 + 3 (index.html) -> pytest.\n"
    "Commits apos cada alteracao."
)

print(f"Resolvendo 3 pendencias...", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
