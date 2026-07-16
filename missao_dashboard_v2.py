"""
Missao: AFP-Team implementa 7 melhorias no dashboard + atualiza contextos.
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
    "Implementar 7 melhorias no dashboard (src/dashboard/index.html + server.py) "
    "e atualizar contextos com o aprendizado.\n\n"

    "1. FECHAR MODAL DE LOGS:\n"
    "Adicionar botao 'X' (fechar) no canto superior direito do .logs-panel-header. "
    "Ao clicar, esconde o painel (display:none). "
    "O 'X' deve ser visivel tanto em tema claro quanto escuro.\n\n"

    "2. INDICADOR DE EXECUCAO EM TEMPO REAL (LIVE STREAM):\n"
    "O SSE ja entrega eventos agent_event com agent_id + status (running/completed/failed). "
    "O handleAgentEvent() ja atualiza agentState.status e renderiza o card. "
    "Mas nao ha indicacao VISUAL OBVIA de que um agente esta rodando. "
    "Melhorar:\n"
    "  a) O card do agente running deve ter uma borda pulsante/animada (CSS animation)\n"
    "  b) O nome da missao/task atual deve aparecer em destaque\n"
    "  c) Quando um agente completa, mostrar brevemente um flash verde no card "
    "e exibir o resultado (success/failed) com a duracao\n"
    "  d) Adicionar .agent-card.running { animation: pulse-border 1.5s infinite } "
    "no CSS e animar @keyframes pulse-border\n\n"

    "3. DOIS MARCADORES IDLE (um so):\n"
    "Atualmente o card mostra 'IDLE' (badge com status-dot) E abaixo 'idle' (sub-status). "
    "Isso e redundante. Unificar:\n"
    "  a) Se status='ready' ou 'idle': mostrar apenas um badge 'IDLE' com o dot, "
    "sem sub-status\n"
    "  b) Se status='running': mostrar badge 'RUNNING' + sub-status com o que esta "
    "executando (ex: 'refactor_code')\n"
    "  c) Se status='completed'/'failed': badge correspondente + sub-status "
    "com a task executada\n"
    "  d) Remover a div.sub-status quando status for idle\n\n"

    "4. CONSUMO DE CONTEXTO:\n"
    "A API /api/context retorna {agents:{id:{context_size_bytes,has_context,...}}} "
    "mas o frontend exibe 'Context: 0%' sempre. "
    "Isso porque nao ha nenhum tracking real de contexto dos arquivos CONTEXTO.md. "
    "Criar no backend (server.py) um endpoint /api/context que calcule:\n"
    "  - has_context: se o arquivo contexts/<project>/<agent>/CONTEXTO.md existe\n"
    "  - context_size_bytes: tamanho do arquivo em bytes\n"
    "  - context_pct: porcentagem baseada em 10KB como 100%\n"
    "Usar Path() para ler os arquivos. Nao mexer no schema de agentes.\n"
    "No frontend, o context-bar ja existe mas mostra 0%. "
    "Garantir que API.fetchContext() receba o novo formato e exiba "
    "'Context: X% (X.X KB)' no .context-text.\n\n"

    "5. MODELO LLM UTILIZADO:\n"
    "Adicionar no card do agente (abaixo do LLM select) uma linha mostrando "
    "o modelo REALMENTE utilizado na ultima execucao: "
    "'Ultimo: opencode_zen/deepseek-v4-pro' ou 'Nenhuma execucao ainda'. "
    "Esse dado vem do agentState.lastExecution que e populado via SSE. "
    "Se agentState.lastExecution existir, exibir agentState.lastExecution.model "
    "ou extrair do payload event.metrics.provider/model.\n\n"

    "6. ULTIMO CICLO DE EXECUCAO NA TELA INICIAL:\n"
    "Na view de projetos (home), abaixo dos cards de projeto, adicionar "
    "uma secao 'Ultima Execucao' que mostra o resumo da missao mais recente.\n"
    "  a) Buscar de /api/missions o resultado mais recente\n"
    "  b) Mostrar: project, num agentes envolvidos, status geral, duracao total\n"
    "  c) Clicavel para navegar ate a view de detalhe daquele projeto\n"
    "Se nao houver missoes, mostrar 'Nenhuma execucao recente'.\n\n"

    "7. CLICK AGENT → LOGS + MODELO:\n"
    "O click no card de agente ja abre logs filtrados. "
    "Adicionar tambem no topo dos logs filtrados uma linha mostrando "
    "'Filtrado: <agent_name> | Ultimo modelo: <model_used>' "
    "para dar contexto rapido. Se ainda nao tiver modelo, mostrar '—'.\n\n"

    "REGRAS:\n"
    "- Todas as edicoes usar refactor_code (NUNCA write_file em arquivo existente)\n"
    "- Apos cada alteracao no index.html: git add + git commit\n"
    "- Apos alteracao no server.py: git add + git commit\n"
    "- DEV faz as implementacoes, QA revisa cada uma\n"
    "- AO FINAL: QA roda pytest tests/ -v e reporta resultado\n"
    "- DEV atualiza contexts/AFP-Team/dev/CONTEXTO.md com licao: "
    "'Sempre verificar se testes passam antes de commitar codigo novo'"
)

context = (
    "src/dashboard/index.html ~1800 linhas com CSS inline e JS inline. "
    "src/dashboard/server.py ~350 linhas com endpoints REST. "
    "contexts/ diretorio com CONTEXTO.md para cada agente. "
    "API ja existente: /api/context, /api/missions, /api/events, /api/agent-config. "
    "SSE em /api/events/stream com eventos agent_event. "
    "state.agentsState mantem status, events, lastExecution, context de cada agente. "
    "Nao introduzir frameworks externos. Nao criar novos arquivos JS/CSS."
)

print(f"Delegando 7 melhorias... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective, "context": context})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
    if s.get("status") == "failure":
        res = s.get("result", {})
        if isinstance(res, dict):
            for k in ("error","rationale"):
                v = res.get(k,"")
                if v: print(f"          {k}: {str(v)[:300]}")
