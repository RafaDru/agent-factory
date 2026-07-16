"""
Missao C: Interaction Flow agrupado por ciclo de missao.
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
    "Refatorar renderTimeline() em src/dashboard/index.html para agrupar "
    "eventos por trace_id/task_id (ciclo de missao) em vez de lista linear.\n\n"

    "Atual: renderTimeline() (~linha 1610) lista allEvents como itens "
    "individuais sequenciais.\n\n"

    "Novo comportamento:\n"
    "1. Agrupar allEvents por event.task_id (ou event.trace_id se task_id vazio). "
    "Cada grupo = uma 'missao'.\n"
    "2. Para cada grupo, renderizar um mission-card:\n"
    "   - <div class='mission-card'> com borda e padding\n"
    "   - Cabecalho: 'Mission: {task_id}' + status final + timestamps\n"
    "   - Dentro: steps conectados por setas (→) entre agentes\n"
    "   - Cada step: {emoji} {agent_id}: {message}\n"
    "3. Eventos sem task_id/trace_id ficam em 'Uncategorized'.\n"
    "4. A seta (→) aparece entre steps consecutivos de agentes DIFERENTES.\n"
    "5. CSS para .mission-card, .mission-header, .mission-step, .mission-arrow.\n\n"

    "Formato: refactor_code. Commits apos. QA revisa. pytest tests/ -v."
)

print(f"Delegando Missao C... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
