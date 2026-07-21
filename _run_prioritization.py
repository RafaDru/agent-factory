import sys, json
sys.path.insert(0, '.')
from src.registry import get_registry
from src.project_discovery import register_discovered_projects

registry = get_registry()
register_discovered_projects(registry)

coordinator = registry.load_agent('AFP-Team', 'coordenador')
print(f"Coordenador: {type(coordinator).__name__}")

subs = {}
for aid in ['dev', 'qa', 'designer', 'arquiteto', 'negocios']:
    agent = registry.load_agent('AFP-Team', aid)
    subs[aid] = agent
    print(f"  + subordinado: {aid} ({type(agent).__name__})")
coordinator.set_subordinates(subs)

result = coordinator.execute({
    "task_id": "missao-priorizar-console-afp",
    "action": "plan_and_execute",
    "goal": """
        Priorizar o backlog do Console AFP e comecar a implementar.

        O dashboard agora se chama Console AFP. Temos 6 epics:
        E-001: Live Stream (monitoramento em tempo real)
        E-002: Configuracao de Projetos, Times e Agentes
        E-003: Home e Navegacao
        E-004: Log e Debug
        E-006: CLI Tooling

        Documentos de referencia:
        - docs/backlog.md (epics detalhados)
        - docs/console-afp-requisitos.md (requisitos de cada tela)
        - docs/console-afp-schema.md (schema canonico)

        Passo 1: Consultar negocios para analisar e priorizar os epics.
        Passo 2: Com base na prioridade, executar as atividades com designer, dev e qa.
    """,
    "context": "Consultar negocios primeiro para definir prioridades. Depois executar em ordem.",
})

status = result.get('status', '?')
print(f"\nResultado: {status}")
print(f"Output: {json.dumps(result, indent=2, default=str)[:3000]}")
