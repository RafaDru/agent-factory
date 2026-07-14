"""
Missao: AFP-Team refaz o dashboard com todas as especificacoes do usuario.
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
    notifier = registry.get_notifier("AFP-Team")

    print("=" * 60)
    print("  AFP-TEAM: Redesign completo do Dashboard")
    print("=" * 60)

    agents = {}
    for aid in ("dev", "qa", "designer", "coordenador"):
        agent = registry.load_agent("AFP-Team", aid)
        agents[aid] = agent
        llm = type(agent._llm).__name__ if getattr(agent, '_llm', None) else 'NONE'
        print(f"  {aid}: {type(agent).__name__} [{llm}]")

    coord = agents["coordenador"]
    coord.set_subordinates({
        "dev": agents["dev"],
        "qa": agents["qa"],
        "designer": agents["designer"],
    })

    # Objetivo detalhado com todas as especificacoes do usuario
    objective = (
        "Redesenhar completamente o dashboard do Agent Factory Platform "
        "(src/dashboard/index.html e server.py) seguindo estas especificacoes:\n\n"

        "ARQUITETURA DE NAVEGACAO:\n"
        "1. Tela inicial: Cards grandes de cada Projeto com stats resumidos "
        "(qtd times, qtd agentes, total execucoes, agentes em operacao agora). "
        "Destaque visual com glass morphism e neon accents.\n"
        "2. Clicando no Projeto: Cards dos Times com metadados e detalhes.\n"
        "3. Clicando no Time: Grid de Agent Cards + painel lateral de fluxo de interacoes.\n\n"

        "CARD DE AGENTE (cada card deve ter):\n"
        "- Avatar circular com icone/emoji no topo superior esquerdo\n"
        "- Status principal em destaque: RUNNING (pulsando), READY, STOPPED, FAILED\n"
        "- Sub-status abaixo do principal: ex 'thinking', 'planning', 'executing', 'reviewing'\n"
        "- Timer de execucao (contagem regressiva ou progressiva)\n"
        "- Ao centro do card: nome da TAREFA atual (mais relevante) e nome da MISSAO (secundario)\n"
        "- Indicador do modo LLM: AUTO / CLOUD / LOCAL + nome do modelo em uso\n"
        "- Barra grafica de contexto (% utilizado) com cor (verde <50%, amarelo <80%, vermelho >80%)\n"
        "- Ultima execucao resumida: DataHora / Missao / Tarefa / Status / Duracao\n\n"

        "PAINEL DE FLUXO DE INTERACOES:\n"
        "- Estilo timeline/conversa: lado esquerdo = coordenador, lado direito = agente acionado\n"
        "- Setas ou conectores visuais indicando quem chamou quem\n"
        "- Cada item da timeline clicavel: expande card flutuante com:\n"
        "  * Insumos (inputs) passados para o agente\n"
        "  * Resultado (output) retornado\n"
        "- Logs acessiveis via menu horizontal no topo da view do time\n\n"

        "ESTILO VISUAL:\n"
        "- Glass morphism (backdrop-filter: blur)\n"
        "- Neon accents (cyan #22d3ee, purple #a855f7)\n"
        "- Dark mode profundo (#0a0a0f)\n"
        "- Animacoes suaves (pulse para running, fade para transicoes)\n"
        "- Tipografia Inter ou system-ui\n"
        "- CSS/JS inline, sem frameworks externos\n"
        "- Responsivo\n\n"

        "DADOS:\n"
        "- Eventos em tempo real via SSE (/api/events/stream)\n"
        "- Metadados de projetos/times via /api/projects\n"
        "- Missoes ativas via /api/missions\n"
        "- Manter compatibilidade com endpoints existentes"
    )

    context = (
        "O dashboard atual tem ~2500 linhas em src/dashboard/index.html "
        "e ~340 linhas em src/dashboard/server.py. "
        "Os endpoints existentes sao: /api/events, /api/events/stream (SSE), "
        "/api/status, /api/context, /api/projects (retorna projects com teams e agents), "
        "/api/missions, /api/debug. "
        "EventNotifier em src/protocols/events.py emite eventos com agent_id, status, "
        "task_id, message, metrics (duration_ms, context), payload, timestamp. "
        "O dashboard DEVE ser um unico arquivo HTML com CSS e JS inline. "
        "NAO usar frameworks externos (React, Vue, etc). "
        "Apenas vanilla HTML+CSS+JS. "
        "Substituir COMPLETAMENTE o index.html atual. "
        "Manter o server.py funcionando com todos os endpoints atuais."
    )

    print(f"\n  Objetivo: {len(objective)} chars de especificacoes")
    print(f"  Contexto: {len(context)} chars")
    print("  Iniciando plan_and_execute...\n")

    result = coord.execute({
        "action": "plan_and_execute",
        "goal": objective,
        "context": context,
    })

    print("=" * 60)
    print("  RESULTADO")
    print("=" * 60)
    print(f"  Status:    {result['status']}")
    print(f"  Mission:   {result.get('mission_id','?')}")
    print(f"  Steps:     {result['total_steps']}")
    print(f"  OK:        {result['completed']}")
    print(f"  Fail:      {result['failed']}")
    print(f"  Skip:      {result['skipped']}")
    print()
    for s in result.get("steps", []):
        ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
        print(f"  [{ok}] {s['step']:40s} {s['agent_id']:10s} {s['status']}")

    # Save summary
    mid = result.get("mission_id","")
    if mid:
        sf = Path(".agent-factory") / "missions" / mid / "_result_summary.json"
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  Resumo: {sf}")
        print(f"  Dir:    .agent-factory/missions/{mid}/")

    return result

if __name__ == "__main__":
    start = time.time()
    try:
        r = main()
        print(f"\n  Tempo total: {time.time()-start:.0f}s")
    except Exception as e:
        print(f"\n  ERRO: {e}")
        import traceback; traceback.print_exc()
