"""
Missao: AFP-Team corrige os bugs do dashboard recém-gerado.
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
    print("  AFP-TEAM: Correcao de bugs no Dashboard")
    print("=" * 60)

    agents = {}
    for aid in ("dev", "qa", "coordenador"):
        agent = registry.load_agent("AFP-Team", aid)
        agents[aid] = agent
        llm = type(agent._llm).__name__ if getattr(agent, '_llm', None) else 'NONE'
        print(f"  {aid}: {type(agent).__name__} [{llm}]")

    coord = agents["coordenador"]
    coord.set_subordinates({
        "dev": agents["dev"],
        "qa": agents["qa"],
    })

    objective = (
        "Corrigir todos os bugs no dashboard em src/dashboard/index.html. "
        "A API /api/projects retorna dados no formato JSON plano, "
        "mas o JavaScript do dashboard espera campos com nomes diferentes "
        "e uma estrutura aninhada que nao existe.\n\n"

        "FORMATO REAL DA API (cada projeto retorna):\n"
        "```json\n"
        '{"project_id": "AFP-Team", "project_name": "Agent Factory Platform", '
        '"team_name": "Agent Factory Platform Team", "icon": "\\u2699\\ufe0f", '
        '"agent_emojis": {"coordenador": "\\ud83c\\udfaf", ...}, '
        '"agents": [{"agent_id": "coordenador", "emoji": "\\ud83c\\udfaf", ...}]}\n'
        "```\n\n"

        "BUGS IDENTIFICADOS (todos no JS de index.html):\n\n"
        "1. project.name nao existe → API retorna project_name (linha ~1083)\n"
        "2. project.id nao existe → API retorna project_id (linhas ~1082, 1014, 1018, 1114, 1142)\n"
        "3. project.teams nao existe → API retorna agents[] diretamente no projeto, sem nested teams (linhas ~1068, 1069, 1074, 1075, 1119)\n"
        "4. agent.id nao existe → API retorna agent_id (linhas ~1076, 1159, 1346)\n"
        "5. project.total_executions e project.active_agents nao existem na API (linhas ~1070, 1071)\n"
        "6. team.name e team.id nao existem → API tem team_name no nivel do projeto, nao em nested array (linhas ~1019, 1128, 1129, 1147)\n"
        "7. Clicar no card de projeto navega com project.id (undefined) → causa 'Project not found'\n\n"

        "SOLUCAO RECOMENDADA:\n"
        "Normalizar os dados da API no loadInitialData() para criar a estrutura "
        "que o UI espera (project → teams[] → agents[]). Assim o resto do JS "
        "funciona sem precisar reescrever todas as views.\n\n"

        "Exemplo de normalizacao:\n"
        "```js\n"
        "state.projects = (projects || []).map(p => ({\n"
        "    id: p.project_id,\n"
        "    name: p.project_name || p.project_id,\n"
        "    icon: p.icon || '📁',\n"
        "    teams: [{\n"
        "        id: p.team_id || p.project_id,\n"
        "        name: p.team_name || 'Team',\n"
        "        agents: (p.agents || []).map(a => ({ id: a.agent_id, ...a }))\n"
        "    }],\n"
        "}));\n"
        "```\n\n"
        "E corrigir as referencias que ainda usam project.name, project.id, agent.id "
        "para os nomes corretos apos normalizacao (project.name vira project_name, etc).\n"
        "Na pratica, a normalizacao ja resolve project.id e project.name. "
        "Mas agent.id nos templates de renderTeamDetail() e no loadInitialData "
        "precisa ser agent_id (antes da normalizacao) ou ja fica id (depois).\n\n"

        "REGRAS:\n"
        "- Usar refactor_code para modificar index.html\n"
        "- NUNCA usar generate_code no mesmo arquivo duas vezes\n"
        "- Nao quebrar o server.py\n"
        "- Nao mudar o CSS ou HTML, apenas o JavaScript\n"
        "- Manter compatibilidade com todos os endpoints existentes\n"
        "- Apos corrigir, verificar que o dashboard carrega sem erros no console"
    )

    context = (
        "O dashboard foi gerado pela propria AFP-Team na ultima missao "
        "(missao-redesenhar-completamente-dashboard-agent-factory-platform). "
        "O arquivo esta em src/dashboard/index.html (~1388 linhas). "
        "O server.py em src/dashboard/server.py serve /api/projects. "
        "Nao altere server.py, apenas index.html. "
        "Teste com refresh no navegador apos cada alteracao."
    )

    print(f"\n  Objetivo: {len(objective)} chars")
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
