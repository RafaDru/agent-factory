"""
Missao: AFP-Team corrige 5 pontos visuais do dashboard.
"""
import sys
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
agents = {}
for aid in ("dev", "qa", "coordenador"):
    agents[aid] = registry.load_agent("AFP-Team", aid)
coord = agents["coordenador"]
coord.set_subordinates({"dev": agents["dev"], "qa": agents["qa"]})

objective = (
    "Corrigir 5 problemas visuais no dashboard (src/dashboard/index.html + server.py):\n\n"

    "PROBLEMA 1 — Painel de logs sem scroll:\n"
    "O div #log-entries nao tem overflow-y:auto nem altura maxima definida.\n"
    "Adicionar no CSS (#logs-panel ou #log-entries):\n"
    "  max-height: 400px; overflow-y: auto;\n"
    "Se ja existir, ajustar para funcionar.\n\n"

    "PROBLEMA 2 — Logs em ordem crescente (antigo primeiro):\n"
    "A API retorna eventos ordenados por timestamp DESC (novo primeiro). "
    "Mas loadPastEvents() itera na ordem da API e usa insertBefore, "
    "resultando em ordem crescente (antigo no topo).\n"
    "Corrigir: em loadPastEvents(), inverter o array antes de iterar:\n"
    "  const events = (data.events || data).reverse();\n"
    "Assim os eventos mais recentes aparecem no topo.\n\n"

    "PROBLEMA 3 — Agente em running sem indicador visual:\n"
    "Os cards de agente (renderTeamDetail ou renderAgentCard) devem mostrar:\n"
    "  - Um ponto colorido (verde=success, amarelo=running, vermelho=failed, cinza=idle)\n"
    "  - O status atual do agente (idle, running, completed, failed)\n"
    "  - Atualizar em tempo real via SSE event.status\n"
    "Verificar se o codigo de renderizacao de agentes ja tem suporte a status "
    "e se nao tiver, adicionar. O SSE event carrega agent_id + status.\n\n"

    "PROBLEMA 4 — Contextos nao atualizam:\n"
    "Endpoint /api/context?project=X existe em server.py.\n"
    "Mas o frontend pode nao estar chamando ou o retorno nao esta sendo exibido.\n"
    "Verificar se ha chamada fetch('/api/context') no index.html. "
    "Se nao houver, adicionar no loadInitialData() ou no carregamento do agente. "
    "Exibir metricas de contexto no card do agente.\n\n"

    "PROBLEMA 5 — Interaction flow vazio:\n"
    "Interaction flow e a timeline de interacoes entre agentes. "
    "Verificar se ha um container no HTML (ex: #interaction-flow, #timeline). "
    "Se existir mas estiver vazio, preencher com base nos eventos: "
    "cada evento com agent_id + status + timestamp vira um item na timeline. "
    "Mostrar setas entre eventos consecutivos de agentes diferentes. "
    "Se nao existir o container, criar no CSS/HTML/JS.\n\n"

    "TODAS as correcoes usar refactor_code em src/dashboard/index.html. "
    "Nao mexer em server.py a menos que necessario. "
    "DEV faz as correcoes. QA revisa cada uma."
)

context = (
    "src/dashboard/index.html ~1670 linhas. "
    "CSS inline no <style>. "
    "JS inline no <script>. "
    "Eventos via SSE em /api/events/stream. "
    "REST /api/events, /api/context, /api/status existem. "
    "Painel de logs com id=logs-panel, log-entries, logs-toggle. "
    "Nao introduzir frameworks externos."
)

print(f"Delegando correcao dos 5 pontos... ({len(objective)} chars)", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective, "context": context})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:45s} {s['agent_id']:10s} {s['status']}", flush=True)
    if s.get("status") == "failure":
        res = s.get("result", {})
        if isinstance(res, dict):
            for k in ("error","rationale"):
                v = res.get(k,"")
                if v: print(f"          {k}: {str(v)[:300]}")
