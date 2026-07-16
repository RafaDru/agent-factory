"""
Missao: AFP-Team adiciona painel de logs + seletor de modelo LLM no dashboard.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.as_posix())

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

def main():
    registry = get_registry()
    if not registry.project_exists("AFP-Team"):
        registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

    agents = {}
    for aid in ("dev", "qa", "designer", "coordenador"):
        agent = registry.load_agent("AFP-Team", aid)
        agents[aid] = agent

    coord = agents["coordenador"]
    coord.set_subordinates({
        "dev": agents["dev"],
        "qa": agents["qa"],
        "designer": agents["designer"],
    })

    context = (
        "src/dashboard/index.html ~1300 linhas, CSS/JS inline. "
        "Ja tem light/dark mode toggle. "
        "Ja tem EventSource SSE em /api/events/stream. "
        "No header .header-actions ha botoes: Back, Refresh, Theme toggle. "
        "Nao introduzir frameworks externos."
    )

    features = [
        ("Painel de Logs", (
            "Adicionar painel de logs acessiveis no dashboard (src/dashboard/index.html):\n"
            "1. No header .header-actions, adicionar botao 'Logs' ao lado do toggle de tema\n"
            "2. Criar um overlay/panel que mostra eventos SSE em tempo real\n"
            "   - Timestamp, agent_id, status, task_id\n"
            "   - Ultimas 200 entradas, scroll vertical\n"
            "   - Filtro por agente e tipo (status/erro/completo)\n"
            "3. Conectar ao EventSource /api/events/stream (ja existe)\n"
            "4. Botao 'Clear' para limpar logs\n"
            "5. CSS integrado ao design atual (glass morphism no dark, sombra no light)\n"
            "6. Usar refactor_code."
        )),
        ("Seletor de Modelo LLM", (
            "Adicionar seletor de modelo LLM nos cards de agente do dashboard:\n"
            "1. No renderTeamDetail(), substituir 'Mode: AUTO / groq/llama-3.3-70b' "
            "por um dropdown com: AUTO, opencode_zen (deepseek-v4-pro), "
            "groq (llama-3.3-70b), opencode (deepseek-v4-pro)\n"
            "2. Ao selecionar, enviar POST /api/agent-config com agent_id e llm_provider\n"
            "3. Adicionar endpoint /api/agent-config em server.py (GET + POST)\n"
            "4. Salvar config em .agent-factory/agent_config.json\n"
            "5. Carregar config salva ao iniciar\n"
            "Use refactor_code para index.html e refactor_code para server.py."
        )),
    ]

    for feat_name, objective in features:
        print(f"\n{'='*60}")
        print(f"  FEATURE: {feat_name}")
        print(f"{'='*60}")
        sys.stdout.flush()

        result = coord.execute({
            "action": "plan_and_execute",
            "goal": objective,
            "context": context,
        })

        print(f"  Status: {result['status']}")
        print(f"  Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}")
        for s in result.get("steps", []):
            d = s.get("decision","")
            ok = "OK" if d in ("accept","skip") else "XX"
            print(f"  [{ok}] {s['step']:40s} {s['agent_id']:10s} {s['status']}")
        sys.stdout.flush()

        if result.get("failed", 0) > 0:
            print(f"  [!] Feature '{feat_name}' teve falhas.")
            # Get error details
            for s in result.get("steps", []):
                if s.get("status") == "failure":
                    res = s.get("result", {})
                    if isinstance(res, dict):
                        err = res.get("error", "")
                        rat = res.get("rationale", "")
                        if err:
                            print(f"  Error: {err[:400]}")
                        if rat:
                            print(f"  Rationale: {rat[:400]}")
            break

    print(f"\n{'='*60}")
    print(f"  MISSAO CONCLUIDA")
    print(f"{'='*60}")

if __name__ == "__main__":
    start = time.time()
    try:
        main()
        print(f"\nTempo total: {time.time()-start:.0f}s")
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback; traceback.print_exc()
