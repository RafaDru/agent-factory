"""
Missao unificada: AFP-Team implementa light mode + logs + seletor de modelo.
Usa o novo refactor_code que retorna apenas edicoes JSON em vez do arquivo completo.
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.as_posix())

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

def main():
    registry = get_registry()
    if not registry.project_exists("AFP-Team"):
        registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

    agents = {}
    for aid in ("dev", "qa", "coordenador"):
        agent = registry.load_agent("AFP-Team", aid)
        agents[aid] = agent

    coord = agents["coordenador"]
    coord.set_subordinates({
        "dev": agents["dev"],
        "qa": agents["qa"],
    })

    # ================================================================
    # FEATURE 1: LIGHT MODE TOGGLE
    # ================================================================
    f1 = (
        "Adicionar toggle light/dark mode no dashboard (src/dashboard/index.html):\n"
        "1. No final do CSS existente (antes de </style>), adicionar:\n"
        "   - :root[data-theme='dark'] com todas as cores atuais\n"
        "   - :root[data-theme='light'] com fundo #f8f9fa, texto #1a1a2e, cards #fff, cyan #0891b2, purple #7c3aed\n"
        "   - transition: background-color 0.3s, color 0.3s em body e cards\n"
        "2. No header (.header-actions), adicionar botao toggle com icone lua/sol\n"
        "3. No final do <script> (antes de </script>), adicionar funcao toggleTheme():\n"
        "   - Alterna data-theme entre 'dark' e 'light' no :root\n"
        "   - Salva no localStorage('dashboard-theme')\n"
        "   - Carrega tema salvo no DOMContentLoaded\n"
        "   - Padrao: dark\n"
        "Use refactor_code com file_path='src/dashboard/index.html' e instructions detalhadas."
    )

    # ================================================================
    # FEATURE 2: PAINEL DE LOGS ACESSIVEL
    # ================================================================
    f2 = (
        "Adicionar painel de logs acessiveis no dashboard (src/dashboard/index.html):\n"
        "1. No header, adicionar botao 'Logs' ao lado do refresh\n"
        "2. Uma view overlay/panel que mostra os eventos SSE recebidos em tempo real\n"
        "   - Timestamp, agent_id, status, task_id, message\n"
        "   - Scroll infinito com as ultimas 200 entradas\n"
        "   - Filtro por agente e por tipo (status, erro, completo)\n"
        "3. Os logs sao populados via EventSource /api/events/stream (ja existe)\n"
        "4. Botao 'Clear' para limpar logs\n"
        "5. CSS e JS inline, integrados ao design atual (glass morphism no dark, sombra no light)\n"
        "Use refactor_code com file_path='src/dashboard/index.html'."
    )

    # ================================================================
    # FEATURE 3: SELETOR DE MODELO LLM POR AGENTE
    # ================================================================
    f3 = (
        "Adicionar seletor de modelo LLM nos cards de agente (src/dashboard/index.html):\n"
        "1. No card de agente (renderTeamDetail), substituir o texto 'Mode: AUTO / groq/llama-3.3-70b'\n"
        "   por um dropdown/select com opcoes:\n"
        "   - AUTO (smart router)\n"
        "   - opencode (deepseek-v4-pro)\n"
        "   - groq (llama-3.3-70b)\n"
        "   - gemini (gemini-2.5-flash)\n"
        "   - cerebras\n"
        "   - mistral\n"
        "2. Ao selecionar, enviar POST /api/agent-config com { agent_id, llm_provider }\n"
        "3. Adicionar endpoint /api/agent-config no server.py que aceita POST e GET\n"
        "4. Salvar configuracao em .agent-factory/agent_config.json\n"
        "5. Carregar configuracao salva ao iniciar\n"
        "Use refactor_code para index.html e refactor_code para server.py."
    )

    context = (
        "O dashboard tem ~1400 linhas em src/dashboard/index.html "
        "e ~650 linhas em src/dashboard/server.py. "
        "Usa CSS/JS inline, glass morphism, neon accents. "
        "O header tem .header-actions com botoes. "
        "Os agent cards sao renderizados por renderTeamDetail() em JS. "
        "O server.py usa SimpleHTTPRequestHandler. "
        "EventSource SSE em /api/events/stream ja existe. "
        "Nao introduzir frameworks externos."
    )

    # Three separate missions - one per feature
    features = [
        ("Light Mode Toggle", f1),
        ("Painel de Logs", f2),
        ("Seletor de Modelo LLM", f3),
    ]

    for feat_name, objective in features:
        print(f"\n{'='*60}")
        print(f"  FEATURE: {feat_name}")
        print(f"{'='*60}")
        print(f"  Objetivo: {len(objective)} chars")
        sys.stdout.flush()

        result = coord.execute({
            "action": "plan_and_execute",
            "goal": objective,
            "context": context,
        })

        print(f"  Status: {result['status']}")
        print(f"  Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}")
        for s in result.get("steps", []):
            ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
            print(f"  [{ok}] {s['step']:40s} {s['agent_id']:10s} {s['status']}")
        sys.stdout.flush()

        if result.get("failed", 0) > 0:
            print(f"  [!] Feature '{feat_name}' teve falhas. Abortando as proximas.")
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
