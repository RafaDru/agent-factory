"""
Redesign completo do dashboard conforme solicitado.
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
    "Redesign completo da tela de detalhe do projeto em src/dashboard/index.html.\n"
    "read_file antes de cada alteracao. git add + git commit apos cada passo.\n"
    "QA revisa cada passo. pytest tests/ -v no final.\n\n"

    "PASSO 1: REDUZIR CARDS DOS AGENTES EM 30%\n"
    "No CSS, encontrar '.agent-card {' e reduzir:\n"
    "  - padding: de ~16px para 10px\n"
    "  - font-size: reduzir em 2px nos elementos internos\n"
    "  - .agent-name: font-size 0.95rem\n"
    "  - .agent-role: font-size 0.75rem\n"
    "  - .agent-status: font-size 0.65rem, padding 2px 6px\n"
    "  - .task-name: font-size 0.8rem\n"
    "  - .last-model, .context-text: font-size 0.7rem\n"
    "  - gap no .agent-card-header: reduzir\n"
    "Manter a proporcao, apenas reduzir escala.\n\n"

    "PASSO 2: AGENTES EM GRID DE 3 COLUNAS\n"
    "Encontrar '.agents-grid {' e garantir:\n"
    "  display: grid\n"
    "  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))\n"
    "  gap: 12px\n"
    "Se usar 'grid-template-columns: repeat(3, 1fr)' para exato 3 colunas.\n\n"

    "PASSO 3: INTERACTION FLOW ABAIXO DOS AGENTES\n"
    "No HTML do renderTeamDetail():\n"
    "  - Manter .team-detail-layout como UMA coluna (nao duas)\n"
    "  - agentsHtml em cima, timelineHtml em baixo\n"
    "  - Remover .timeline-panel de dentro do layout grid, colocar abaixo\n"
    "  - Adicionar margin-top: 32px entre agents e timeline\n"
    "  - .timeline-panel: width 100%, sem posicao fixa\n\n"

    "PASSO 4: REMOVER 'LAST EXECUTION' do topo\n"
    "Em renderTeamDetail(), remover a linha ${renderLastExecution(project.id)}\n"
    "Manter apenas o agentes grid e o interaction flow.\n\n"

    "PASSO 5: INTERACTION FLOW COLABSAVEL (TREE VIEW)\n"
    "SUBSTITUIR renderTimeline() completamente:\n\n"

    "5.1 Estrutura:\n"
    "  - Cada mission-card e colapsavel (<details>/<summary> ou toggle JS)\n"
    "  - Header: 'Mission: {task_id}' + status + timestamp\n"
    "  - Ao expandir: arvore de agentes\n\n"

    "5.2 Arvore de agentes:\n"
    "  - Cada no (agente) e um card compacto com:\n"
    "    - Header: avatar (emoji) + nome do agente\n"
    "    - Body: task_id + nome da task\n"
    "    - Footer: status + timestamp de inicio\n"
    "  - Se agente A delegou para B: card de B fica IDENTADO (margin-left: 32px)\n"
    "  - Com linha vertical ├── (border-left: 2px solid var(--border-glass)) na indentacao\n"
    "  - Niveis mais profundos: margin-left: 32px adicional + border-left\n\n"

    "5.3 Status visual:\n"
    "  - Borda esquerda do card (4px solid): verde se success, vermelho se failed, amarelo se running\n"
    "  - Background sutil baseado no status\n"
    "  - Texto do status no footer\n\n"

    "5.4 Dados:\n"
    "  - Cada event tem: agent_id, task_id, status, timestamp\n"
    "  - Agrupar por task_id (ja existe)\n"
    "  - Dentro de cada task_id, ordenar por timestamp\n"
    "  - Identar quando agent_id muda entre eventos consecutivos\n\n"

    "5.5 CSS novo:\n"
    "  .mission-card { margin-bottom: 8px; border-radius: 8px; overflow: hidden; }\n"
    "  .mission-header { padding: 8px 12px; cursor: pointer; display: flex; justify-content: space-between; }\n"
    "  .mission-body { padding: 4px 0; }\n"
    "  .agent-node { margin-left: 0; border-left: 2px solid var(--border-glass); padding-left: 12px; margin-bottom: 4px; }\n"
    "  .agent-node.level-1 { margin-left: 32px; }\n"
    "  .agent-node.level-2 { margin-left: 64px; }\n"
    "  .agent-node .node-card { padding: 8px 12px; border-radius: 6px; border-left: 4px solid var(--border-glass); }\n"
    "  .agent-node .node-card.status-success { border-left-color: var(--green); }\n"
    "  .agent-node .node-card.status-failed { border-left-color: var(--red); }\n"
    "  .agent-node .node-card.status-running { border-left-color: var(--yellow); }\n"
    "  .node-header { display: flex; align-items: center; gap: 8px; }\n"
    "  .node-avatar { font-size: 1.2rem; }\n"
    "  .node-name { font-weight: 600; font-size: 0.85rem; }\n"
    "  .node-body { margin: 4px 0 0 28px; font-size: 0.8rem; }\n"
    "  .node-footer { margin: 4px 0 0 28px; font-size: 0.7rem; color: var(--text-secondary); }\n\n"

    "REGRAS:\n"
    "- read_file antes de cada alteracao\n"
    "- git add + git commit apos cada passo\n"
    "- QA revisa cada passo\n"
    "- pytest tests/ -v no final\n"
    "- ATUALIZAR dev/CONTEXTO.md com licoes"
)

print(f"Redesign completo...", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
