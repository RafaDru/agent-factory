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
    "task_id": "missao-implementar-epic002-configuracao",
    "action": "plan_and_execute",
    "goal": """
        Implementar o E-002: Console AFP — Configuracao de Projetos, Times e Agentes.

        O dashboard esta em src/dashboard/index.html (HTML/CSS/JS puro, servido por src/dashboard/server.py).
        Nao use React ou frameworks — mantenha o mesmo estilo do dashboard existente.

        Documentos de referencia:
        - docs/backlog.md (epic E-002 detalhado)
        - docs/console-afp-requisitos.md (requisitos detalhados de cada tela)
        - docs/console-afp-schema.md (schema canonico)
        - src/dashboard/index.html (codigo existente do dashboard)

        Requisitos:
        1. Nova aba/tela de configuracao no dashboard com:
           - CRUD de Projetos (adicionar, editar, excluir)
           - CRUD de Times
           - CRUD de Agentes com preview formatado do CONTEXTO.md
           - Configuracao de LLM provider e model por agente
           - Exibicao de todos os metadados do agente
        2. Usar os endpoints REST ja existentes em src/dashboard/server.py:
           - GET /api/projects -> lista projetos
           - POST /api/agent-config -> atualiza config de agente
           - GET /api/agent-config?agent_id=X -> le config de agente
        3. Integrar no sistema de navegacao existente (abas: Home, Live, Config, Log)
        4. Manter consistencia visual com o dashboard atual

        Design ja aprovado pelo designer e arquiteto na missao anterior:
        - Componentes: EntityTable, EntityForm para CRUD generico
        - AppShell com Sidebar, Header, ContentArea
        - Visual glass morphism + neon accents

        Passos:
        1. designer: revisar design e criar especificacao detalhada da tela de config
        2. dev: implementar a tela de configuracao em src/dashboard/index.html
        3. qa: revisar o codigo implementado e testar
        4. arquiteto: revisar arquitetura da implementacao
    """,
    "context": "Implementar apenas E-002. Nao misturar com outros epics.",
})

status = result.get('status', '?')
print(f"\nResultado: {status}")
print(f"Output: {json.dumps(result, indent=2, default=str)[:5000]}")
