"""
Missao follow-up: corrigir interaction flow + contexto frontend + ultima execucao + click com modelo.
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
    "Missao anterior completou 4 das 7 melhorias. Restam 3 pendentes:\n\n"

    "PENDENCIA A — CONTEXTO NO FRONTEND (bloqueado por dependencia):\n"
    "O backend (server.py) ja foi atualizado com endpoint /api/context que "
    "retorna {agents: {id: {context_size_bytes, has_context, context_pct}}}. "
    "Mas o frontend (index.html) ainda nao consome esse novo formato.\n"
    "Corrigir:\n"
    "1) Ler a funcao fetchContext em index.html (API.fetchContext). "
    "Ela deve retornar o JSON completo.\n"
    "2) Em renderTeamDetail(), onde chama API.fetchContext(project.id), "
    "adaptar para usar o NOVO formato: data.agents[agentId].context_pct "
    "em vez de data[agentId].\n"
    "3) updateAgentContext() deve exibir 'Context: X% (X.X KB)' "
    "usando os campos context_pct e context_size_bytes.\n\n"

    "PENDENCIA B — ULTIMA EXECUCAO NA TELA INICIAL:\n"
    "A tela inicial (lista de projetos) deve ter uma secao "
    "'Ultima Execucao' mostrando o resultado da missao mais recente.\n"
    "1) O endpoint /api/missions ja existe em server.py? Se sim, consumir.\n"
    "2) Se nao existir, o server.py tem /api/status. Consumir /api/status "
    "para obter ultimo phase/progress.\n"
    "3) Ou consumir /api/events?limit=1 para mostrar ultimo evento.\n"
    "4) Exibir abaixo dos cards de projeto: project, num agentes, status, "
    "timestamp. Clicavel para navegar ao projeto.\n"
    "5) Se nao houver nada, mostrar 'Nenhuma execucao recente'.\n\n"

    "PENDENCIA C — CLICK AGENT + MODELO NOS LOGS:\n"
    "Melhoria-7 falhou porque o anchor '.logs-close-btn:hover' nao foi encontrado.\n"
    "O arquivo index.html pode estar em estado inconsistente (commits parciais).\n"
    "Ler o index.html atual com read_file, analisar a estrutura, e entao:\n"
    "1) No click handler de agent-card (ja existe), apos abrir o painel e "
    "setar filtro, tambem exibir no topo dos logs uma linha como:\n"
    "   '<div class=\"log-filter-info\">Filtrado: coordenador | Ultimo modelo: —</div>'\n"
    "2) Se agentState.lastExecution existir e tiver model/provider, exibir.\n"
    "3) Usar refactor_code com anchors UNICOS (buscar texto exato ao redor).\n"
    "Se mesmo assim falhar, criar uma string old completa com 10 linhas de contexto.\n\n"

    "REGRAS:\n"
    "- DEV implementa, QA revisa cada pendencia\n"
    "- Apos cada mudanca: git add + git commit\n"
    "- AO FINAL: QA roda pytest tests/ -v e reporta\n"
    "- dev atualiza seu CONTEXTO.md com licao: 'Nova feature sempre testar local primeiro'"
)

context = (
    "src/dashboard/index.html ~1817 linhas. "
    "src/dashboard/server.py ~370 linhas. "
    "API.fetchContext existe como funcao global. "
    "state.agentsState tem campo 'context' que recebe valor numerico. "
    "renderTeamDetail() em ~linha 1240 chama API.fetchContext. "
    "logs-close-btn e novo botao X adicionado na melhoria anterior. "
    "Click handler de agent-card usa document.addEventListener('click')."
)

print(f"Delegando follow-up... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective, "context": context})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
