"""
Missao: corrigir context + interaction flow + atualizar contexto dev.
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
    "Os 3 ultimos bugs sao todos no mesmo arquivo (server.py ou index.html):\n\n"

    "BUG 1 — Contexto retorna agentes vazio:\n"
    "Arquivo: src/dashboard/server.py\n"
    "Funcao: _list_agent_ids() na linha ~400\n"
    "Problema: so retorna agentes que tem eventos no notifier.get_events(). "
    "Se o notifier nunca recebeu eventos (ex: apos restart), retorna [] vazio, "
    "e o /api/context retorna agents vazio.\n"
    "Corrigir: FALLBACK para ler diretorios do filesystem:\n"
    "  contexts_dir = Path('contexts') / project_id\n"
    "  if contexts_dir.exists():\n"
    "      for d in contexts_dir.iterdir():\n"
    "          if d.is_dir() and (d / 'CONTEXTO.md').exists():\n"
    "              seen.add(d.name)\n"
    "Assim mesmo sem eventos no notifier, os agentes com CONTEXTO.md serao listados.\n\n"

    "BUG 2 — Interaction flow nao carrega historico:\n"
    "Arquivo: src/dashboard/index.html\n"
    "O codigo que carrega eventos historicos esta dentro de switchView() "
    "mas state.agentsState[id] pode nao existir para todos os agentes "
    "(ex: 'designer' pode nao ter sido inicializado se o projeto nao o listou).\n"
    "Corrigir: onde faz 'if (agentId && state.agentsState[agentId])' "
    "trocar para criar state.agentsState[agentId] se nao existir:\n"
    "  if (agentId && !state.agentsState[agentId]) {\n"
    "    state.agentsState[agentId] = { status:'ready', subStatus:'idle', task:null, mission:null, timer:0, timerStart:null, context:0, lastExecution:null, events: [] };\n"
    "  }\n"
    "  if (agentId && state.agentsState[agentId]) { ... }\n\n"

    "BUG 3 — Erro ao carregar eventos passados (Failed to fetch):\n"
    "Arquivo: src/dashboard/index.html\n"
    "O erro 'Failed to load resource: net::ERR_EMPTY_RESPONSE' ocorre "
    "no loadPastEvents() ao fazer fetch('/api/events'). "
    "Pode ser que o endpoint /api/events esteja demorando ou retornando vazio. "
    "Adicionar try/catch mais robusto e timeout de 5s no fetch.\n"
    "Corrigir: em loadPastEvents(), usar AbortController com timeout:\n"
    "  const controller = new AbortController();\n"
    "  setTimeout(() => controller.abort(), 5000);\n"
    "  const res = await fetch('/api/events', { signal: controller.signal });\n"
    "E no catch, apenas logar warning em vez de error.\n\n"

    "REGRAS:\n"
    "- DEV implementa, QA revisa\n"
    "- Commits apos cada alteracao\n"
    "- QA roda pytest tests/ -v no final\n"
    "- DEV atualiza seu CONTEXTO.md com secao 'Licoes Aprendidas' "
    "adicionando bullet: "
    "'Sempre tratar o caso de estado vazio (notifier sem eventos, agentsState sem entry) "
    "com fallback para filesystem ou inicializacao lazy.'"
)

print(f"Delegando 3 bugs finais... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
