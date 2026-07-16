"""
Missao v3: 5 melhorias no dashboard.
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
    "5 melhorias no dashboard (src/dashboard/index.html). "
    "NENHUMA alteracao em server.py.\n\n"

    "1. ESPACAMENTO entre agentes e Interaction Flow:\n"
    "No CSS, .team-detail-layout usa grid/flex com duas colunas. "
    "Adicionar gap: 24px entre a coluna de agentes e a timeline. "
    "Se ja existir gap, aumentar para 24px. "
    "Usar refactor_code com o seletor CSS exato .team-detail-layout.\n\n"

    "2. STATUS AO VIVO (SSE sem recriar DOM):\n"
    "Problema: handleAgentEvent() chama renderTeamDetail() que faz "
    "container.innerHTML = ... destruindo TODO o DOM a cada evento. "
    "Isso causa flickering e perda de estado visual.\n"
    "Corrigir: handleAgentEvent (~linha 1290) deve ATUALIZAR apenas o card "
    "do agente afetado, nao recriar a pagina inteira.\n"
    "Criar funcao updateAgentCard(agentId) que:\n"
    "  a) Encontra o card existente: document.getElementById('agent-'+agentId)\n"
    "  b) Atualiza o status badge: .agent-status .status-dot + texto\n"
    "  c) Atualiza o task-name e mission-name\n"
    "  d) Atualiza o timer se running\n"
    "  e) Atualiza ou remove sub-status (se nao existir um elemento, NAO criar)\n"
    "  f) Adiciona/remove classes CSS: .running, .success, .failed\n"
    "  g) Nao mexe no resto do card (LLM select, context bar, etc)\n"
    "handleAgentEvent deve chamar updateAgentCard(agentId) em vez de "
    "renderTeamDetail(). Chamar renderTeamDetail() apenas quando nao existir "
    "card (ex: primeira carga ou navegacao).\n"
    "Dica: guardar 'if (!document.getElementById('agent-'+agentId)) renderTeamDetail();'\n\n"

    "3. TIMESTAMP no Interaction Flow:\n"
    "renderTimeline() renderiza .timeline-item com nome do agente e mensagem. "
    "Adicionar o timestamp formatado (toLocaleString) em cada item, "
    "num span com classe 'timeline-time', logo abaixo da mensagem.\n\n"

    "4. INTERACTION FLOW por CICLO de MISSÃO:\n"
    "Hoje: lista linear de eventos individuais (QA:fez X, QA:fez Y, DESIGNER:fez Z...).\n"
    "Desejado: agrupar eventos pelo 'trace_id' (cada missao/task tem um trace_id unico). "
    "Cada grupo vira um 'card de missao' com:\n"
    "  - Nome/cabecalho da missao (task_id ou 'Mission #...')\n"
    "  - Lista de passos dentro da missao, com setas indicando quem acionou quem\n"
    "  - Status final da missao (SUCCESS/FAILED/RUNNING)\n"
    "  - Timestamp de inicio e fim\n"
    "Modificar renderTimeline() para:\n"
    "  a) Agrupar allEvents por event.trace_id ou event.task_id\n"
    "  b) Para cada grupo, renderizar um mission-card com cabecalho\n"
    "  c) Dentro do mission-card, renderizar os passos com setas direcionais\n"
    "  d) Se nao houver trace_id, mostrar como 'Uncategorized'\n"
    "  e) Manter o empty state se nao houver eventos\n\n"

    "5. INTERNACIONALIZACAO (i18n):\n"
    "Criar objeto global L (const L = {...}) no inicio do <script> "
    "com TODAS as strings da UI em INGLES.\n"
    "Substituir todos os textos hardcoded nos templates JS por L.xxx.\n"
    "Mapear strings atualmente em portugues para ingles:\n"
    "  'Projetos' → 'Projects'\n"
    "  'Voltar' → 'Back'\n"
    "  'Ultimo:' → 'Last:'\n"
    "  'Nenhuma execucao ainda' → 'No executions yet'\n"
    "  'Context:' → 'Context:'\n"
    "  'No active task' → 'No active task' (ja em ingles)\n"
    "  'Interaction Flow' → 'Interaction Flow' (ja em ingles)\n"
    "  'No interactions yet' → 'No interactions yet' (ja em ingles)\n"
    "  'Event Logs' → 'Event Logs' (ja em ingles)\n"
    "  'All Agents' → 'All Agents' (ja em ingles)\n"
    "  'All Types' → 'All Types' (ja em ingles)\n"
    "  'AGENTS' → 'AGENTS' (ja em ingles)\n"
    "  'ACTIVE' → 'ACTIVE' (ja em ingles)\n"
    "  'Ultima Execucao' → 'Last Execution'\n"
    "  'Nenhuma execucao recente' → 'No recent executions'\n"
    "  'Filtrado:' → 'Filtered by:'\n"
    "  'Close' → 'Close'\n"
    "  'Clear' → 'Clear'\n"
    "  'Timeline' → 'Timeline'\n"
    "  'Logs' → 'Logs'\n"
    "Formato: const L = { close: 'Close', logs: 'Logs', back: 'Back', ... };\n"
    "Depois usar ${L.close} no lugar de 'Close', etc.\n"
    "IMPORTANTE: Nao traduzir nomes de agentes, projetos, ou dados dinamicos. "
    "So traduzir LABELS FIXOS da interface.\n\n"

    "Ordem: 1 (CSS) → 5 (i18n, mexe em todos os templates) → 2 (SSE live update) "
    "→ 3 (timestamp) → 4 (group by mission) → tests.\n"
    "Commits apos cada passo. QA revisa cada passo. "
    "No final: pytest tests/ -v.\n"
    "DEV atualiza seu CONTEXTO.md com licao: 'SSE events devem atualizar DOM "
    "seletivamente, nunca recriar o container inteiro.'"
)

print(f"Delegando 5 melhorias... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
