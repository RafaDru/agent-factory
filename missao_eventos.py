"""
Missao: AFP-Team corrige pipeline de eventos e QA implementa testes automatizados.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
if not registry.project_exists("AFP-Team"):
    registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

agents = {}
for aid in ("dev", "qa", "designer", "coordenador"):
    agents[aid] = registry.load_agent("AFP-Team", aid)

coord = agents["coordenador"]
coord.set_subordinates({
    "dev": agents["dev"],
    "qa": agents["qa"],
    "designer": agents["designer"],
})

objective = (
    "Corrigir o pipeline de eventos do Agent Factory para que o dashboard mostre "
    "indicadores em tempo real dos agentes atuando, e o QA implemente testes automatizados "
    "que validem o fluxo completo.\n\n"

    "PROBLEMA 1 — Eventos nao chegam no dashboard:\n"
    "- O registry cria EventNotifier em registry._notifiers\n"
    "- O DashboardServer cria EventNotifier em DashboardHandler.notifiers\n"
    "- Sao instancias DIFERENTES — eventos emitidos por agentes durante missoes "
    "vao para o notifier do registry, NAO para o notifier do dashboard\n"
    "- O SSE /api/events/stream registra clientes via EventNotifier._sse_clients "
    "(class-level), entao SSE emite events sim, mas somente se o dashboard ESTIVER RODANDO "
    "durante a missao\n"
    "- Para eventos PASSADOS (dashboard aberto depois da missao), o REST /api/events "
    "so retorna eventos do notifier do dashboard, que esta vazio\n"
    "- SOLUCAO: DashboardServer deve obter notifiers do registry (get_registry().get_notifier()) "
    "em vez de criar os seus proprios. Assim eventos de missoes ficam visiveis "
    "tanto via SSE quanto via REST.\n\n"

    "PROBLEMA 2 — Roteamento quebrado no server.py:\n"
    "- do_GET(): os elifs de /api/debug e /api/agent-config estao mal encadeados — "
    "/api/agent-config cai em _serve_debug() em vez de _serve_agent_config()\n"
    "- do_POST(): /api/agent/provider e /api/agent-config com elif mal estruturado\n"
    "- Corrigir o encadeamento de elifs\n\n"

    "PROBLEMA 3 — Painel de logs nao carrega eventos iniciais:\n"
    "- O frontend conecta EventSource('/api/events/stream') mas nao faz fetch inicial "
    "de /api/events para carregar eventos passados\n"
    "- Adicionar fetch /api/events no DOMContentLoaded e exibir no painel de logs\n"
    "- Garantir que o painel mostra: timestamp, agent_id, status, task_id\n\n"

    "TAREFA DO QA:\n"
    "1. Atualizar o contexto do QA em contexts/AFP-Team/qa/CONTEXTO.md "
    "para incluir que o QA deve criar testes automatizados que validem:\n"
    "   - Eventos sao emitidos durante execucao de missoes\n"
    "   - Eventos persistem em .agent-events/<project>/events.jsonl\n"
    "   - REST /api/events retorna eventos apos missao\n"
    "   - SSE entrega eventos em tempo real\n"
    "   - Painel de logs no frontend exibe eventos corretamente\n"
    "2. Criar arquivo de teste tests/test_event_pipeline.py com pytest "
    "que valide todos os pontos acima\n"
    "3. O teste deve ser executavel com: python -m pytest tests/test_event_pipeline.py -v\n\n"

    "Use refactor_code para server.py e index.html. "
    "Use write_file para criar tests/test_event_pipeline.py. "
    "Use refactor_code para contexts/AFP-Team/qa/CONTEXTO.md."
)

context = (
    "src/dashboard/server.py ~736 linhas, src/dashboard/index.html ~1650 linhas. "
    "src/protocols/events.py ~184 linhas. "
    "Nao ha diretorio tests/ ainda — criar. "
    "O registry e singleton via get_registry(). "
    "DashboardHandler.notifiers e dict class-level. "
    "EventNotifier._sse_clients e set class-level (compartilhado entre instancias). "
    "Eventos persistem em .agent-events/<project_id>/events.jsonl (JSONL). "
    "QA context em contexts/AFP-Team/qa/CONTEXTO.md."
)

print(f"Delegando missao ao coordenador... ({len(objective)} chars)", flush=True)
t0 = time.time()
result = coord.execute({
    "action": "plan_and_execute",
    "goal": objective,
    "context": context,
})
print(f"Concluido em {time.time()-t0:.0f}s", flush=True)
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
