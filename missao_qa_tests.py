"""
Missao: AFP-Team cria contexto de QA + testes de pipeline de eventos.
DEV faz a escrita, QA revisa/valida.
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
    "Criar testes automatizados de pipeline de eventos e atualizar contexto do QA.\n\n"

    "IMPORTANTE: QA nao tem write_file/refactor_code. "
    "DEV deve fazer toda criacao/edicao de arquivos. "
    "QA deve apenas revisar e validar.\n\n"

    "TAREFA 1 — DEV: Atualizar contexts/AFP-Team/qa/CONTEXTO.md:\n"
    "Adicionar na secao 'Acoes Disponiveis' a linha:\n"
    "| test_event_pipeline | Executa pytest tests/test_event_pipeline.py -v e valida o pipeline de eventos |\n"
    "Adicionar na secao 'Exemplos' a linha:\n"
    '{"action": "run_tests", "path": "tests/test_event_pipeline.py", "args": ["-v"]}\n'
    "Adicionar ao final uma secao 'Testes de Pipeline de Eventos':\n"
    "  O QA deve validar que:\n"
    "  - Eventos sao emitidos durante execucao de missoes\n"
    "  - Eventos persistem em .agent-events/<project>/events.jsonl\n"
    "  - REST /api/events retorna eventos apos missao\n"
    "  - SSE entrega eventos em tempo real\n"
    "  - Painel de logs no frontend exibe eventos corretamente\n"
    "Use refactor_code com file_path='contexts/AFP-Team/qa/CONTEXTO.md'.\n\n"

    "TAREFA 2 — DEV: Criar tests/test_event_pipeline.py:\n"
    "Testes pytest que validam:\n"
    "1. EventNotifier.emit() persiste evento em .agent-events/<project>/events.jsonl\n"
    "2. EventNotifier.get_events() retorna eventos persistidos\n"
    "3. EventNotifier._notify_sse_clients() envia para clientes registrados\n"
    "4. DashboardHandler._serve_events retorna eventos como JSON\n"
    "5. Registry.get_notifier() retorna mesmo notifier que agentes usam\n"
    "6. DashboardServer inicializa notifiers a partir do registry\n"
    "Use write_file com file_path='tests/test_event_pipeline.py'.\n\n"

    "TAREFA 3 — QA: Revisar context e test file:\n"
    "1. review_code no CONTEXTO.md (validar que as secoes estao corretas)\n"
    "2. review_code no test_event_pipeline.py (validar cobertura)\n"
    "3. run_tests em tests/test_event_pipeline.py -v\n\n"

    "TAREFA 4 — DEV: git add + commit apos cada alteracao."
)

context = (
    "QA agent actions: run_tests, validate_python_syntax, review_code, "
    "suggest_fixes, analyze_project, file_exists, analyze_artifact, lint. "
    "QA NAO tem write_file, edit_file, refactor_code. "
    "DEV que deve criar/editar arquivos. "
    "contexts/AFP-Team/qa/CONTEXTO.md atualmente tem 32 linhas. "
    "tests/ diretorio existe com test_all.py, test_loader.py, "
    "test_context_manager.py, test_orchestrator_extras.py. "
    "EventNotifier em src/protocols/events.py."
)

print(f"Delegando missao... ({len(objective)} chars)", flush=True)
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
            for k in ("error","rationale","summary"):
                v = res.get(k,"")
                if v: print(f"          {k}: {str(v)[:300]}")
