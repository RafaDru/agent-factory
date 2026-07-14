"""
Delega ao Designer do AFP-Team: 2 propostas graficas para o dashboard.
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.as_posix())

from src.registry import get_registry
from src.protocols.schema import ProjectConfig


def run_designer(objective_prompt, label, registry, notifier):
    designer = registry.load_agent("AFP-Team", "designer")
    print()
    print("-" * 60)
    print(f"  DESIGNER: {label}")
    print("-" * 60)
    
    task = {
        "task_id": f"design-{label.lower().replace(' ','-')[:20]}",
        "action": "design_ui",
        "title": label,
        "prompt": objective_prompt,
        "_mission_id": f"proposta-{int(time.time())}",
        "_task_id": label.lower().replace(" ", "-")[:30],
    }
    
    start = time.time()
    result = designer.run(task)
    elapsed = time.time() - start
    
    model = getattr(designer._llm, 'model', type(designer._llm).__name__) if designer._llm else "?"
    print(f"  Status: {result.status.value}  Duration: {elapsed:.1f}s  Model: {model}")
    
    if result.output:
        for k, v in result.output.items():
            if isinstance(v, str) and len(v) > 50:
                print(f"\n  --- {k} ---")
                print(v[:2000])
            elif not isinstance(v, str):
                pass
    
    return result

def main():
    registry = get_registry()
    if not registry.project_exists("AFP-Team"):
        registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))
    notifier = registry.get_notifier("AFP-Team")

    print("=" * 60)
    print("  DESIGNER AFP-TEAM — PROPOSTAS GRAFICAS DO DASHBOARD")
    print("=" * 60)

    base_prompt = """Analise o dashboard atual do Agent Factory Platform (dark mode, cards de agentes,
tabelas de eventos, sidebar colapsavel com navegacao entre projetos) e crie uma proposta de redesign
completa que inclua:

1. Layout geral (estrutura de navegacao, hierarquia visual, disposicao dos elementos)
2. Paleta de cores (background, superficies, acentos, semanticas)
3. Tipografia (fontes, hierarquia, tamanhos)
4. Componentes principais (cards, tabelas, graficos, navegacao)
5. Fluxo de interacao (como o usuario navega entre projetos, agentes, missoes)
6. Esboco textual da estrutura (header, sidebar, content area, etc)"""

    # ─── Proposta 1: Tradicional ───
    trad_prompt = base_prompt + """

ESTILO: TRADICIONAL / CORPORATIVO
- Design limpo e profissional, adequado para ambientes enterprise
- Dark mode mas com toques de cores corporativas (azul escuro, cinza)
- Cards bem definidos, sombras sutis, bordas limpas
- Tabelas de dados classicas com ordenacao e filtros
- Navegacao por abas ou sidebar tradicional
- Graficos de barras e linhas padrao
- Tom serio e confiavel
Inspire-se em: Grafana, Datadog, AWS Console"""

    # ─── Proposta 2: Disruptiva ───
    disrupt_prompt = base_prompt + """

ESTILO: DISRUPTIVO / INOVADOR
- Design arrojado que desafia convencoes de dashboards tradicionais
- Visualizacao de dados nao-convencional (grafos de dependencia, heatmaps, timelines radiais)
- Uso criativo de animacoes, transicoes e microinteracoes
- Navegacao por gestos ou comandos (teclado/atalhos)
- Paleta vibrante com fundo escuro profundo e acentos neon
- Tipografia display para numeros grandes (KPI em destaque)
- Layout que prioriza "o que esta acontecendo AGORA" sobre dados historicos
Inspire-se em: Stripe Dashboard, Linear, Raycast, Nothing OS"""

    run_designer(trad_prompt, "Proposta Tradicional", registry, notifier)
    run_designer(disrupt_prompt, "Proposta Disruptiva", registry, notifier)

    print(f"\n{'='*60}")
    print(f"  Designer concluiu as 2 propostas.")
    print(f"  Artefatos salvos em .agent-factory/missions/proposta-*/")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
