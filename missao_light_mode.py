"""
Missao: AFP-Team adiciona light mode toggle no dashboard (sem designer).
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

    objective = (
        "Adicionar toggle de light mode no dashboard em src/dashboard/index.html.\n\n"
        "ESPECIFICACOES TECNICAS:\n"
        "1. No header (<header>), criar botao toggle ao lado do refresh (dentro do .header-actions)\n"
        "2. Botao com icone: lua (&#9790; ou &#127769;) para dark, sol (&#9728;&#65039; ou &#127774;) para light\n"
        "3. Converter todo o CSS para usar CSS custom properties com data-theme attribute\n"
        "   - :root[data-theme=\"dark\"] = cores atuais (#0a0a0f fundo, cyan #22d3ee, purple #a855f7)\n"
        "   - :root[data-theme=\"light\"] = fundo #f8f9fa, texto #1a1a2e, cyan #0891b2, purple #7c3aed\n"
        "4. JavaScript: toggleTheme() que alterna data-theme entre \"dark\" e \"light\"\n"
        "5. Salvar preferencia no localStorage (chave: \"dashboard-theme\")\n"
        "6. Carregar tema salvo no DOMContentLoaded\n"
        "7. Transicao suave: transition: background-color 0.3s ease, color 0.3s ease\n"
        "8. No light mode: cards com sombra suave (box-shadow) ao inves de glass morphism escuro\n"
        "9. Manter dark mode como padrao (se nunca salvou, comecar dark)\n\n"
        "NAO use designer — apenas dev para implementar e qa para revisar."
    )

    context = (
        "src/dashboard/index.html ~1400 linhas. "
        "Header tem: .header-actions contem botoes de navegacao e refresh (#btnBack, #btnRefresh). "
        "Adicionar o toggle antes ou depois do refresh. "
        "CSS atual usa variaveis soltas (nao tem :root vars ainda). "
        "Converter tudo para CSS vars. "
        "Nao mexer em server.py."
    )

    print(f"Iniciando missao light mode ({len(objective)} chars)...")
    sys.stdout.flush()

    result = coord.execute({
        "action": "plan_and_execute",
        "goal": objective,
        "context": context,
    })

    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}")
    for s in result.get("steps", []):
        ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
        print(f"  [{ok}] {s['step']:40s} {s['agent_id']:10s} {s['status']}")
    sys.stdout.flush()

    return result

if __name__ == "__main__":
    start = time.time()
    try:
        r = main()
        print(f"\nTempo total: {time.time()-start:.0f}s")
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback; traceback.print_exc()
