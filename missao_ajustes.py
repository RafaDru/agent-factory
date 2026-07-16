"""
Ajustes finais no dashboard: cores, botoes, grouping, business agent, auditoria.
"""
import sys
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
registry = get_registry()
agents = {}
for aid in ("dev", "qa"):
    agents[aid] = registry.load_agent("AFP-Team", aid)
coord = registry.load_agent("AFP-Team", "coordenador")
coord.set_subordinates(agents)

objective = (
    "8 ajustes no dashboard e contextos. read_file antes de cada alteracao.\n"
    "git add + git commit apos cada passo. pytest tests/ -v no final.\n\n"

    "1. RUNNING LABEL COLOR (CSS):\n"
    "Em src/dashboard/index.html, encontrar '.status-running' e '.dot-running' "
    "e trocar a cor de amarelo (yellow, #eab308, #f59e0b) para azul (#3b82f6 ou var(--blue)).\n"
    "Fazer o mesmo para .node-card.status-running (borda azul, bg azul claro).\n\n"

    "2. MAIS PADDING NOS CARDS (CSS):\n"
    "Em .agent-card { padding: aumentar de 10px para 14px }\n"
    "Em .agent-card-header { gap: aumentar para 10px }\n\n"

    "3. BOTAO DE LOGS POR AGENTE (JS + CSS):\n"
    "Em renderTeamDetail(), adicionar no card de cada agente um botao "
    "<button class='agent-log-btn' onclick=\"openAgentLog('AGENT_ID')\" title='Logs deste agente'>📋</button> "
    "onde AGENT_ID deve ser substituido por agent.id no template JS. "
    "no canto superior direito do .agent-card-header.\n"
    "Criar funcao global openAgentLog(agentId) que:\n"
    "  - Abre o logs-panel (display:block)\n"
    "  - Chama updateAgentFilterOptions()\n"
    "  - Seta filterAgent.value = agentId\n"
    "  - Chama applyFilters()\n"
    "CSS: .agent-log-btn { background:none; border:none; cursor:pointer; font-size:1rem; opacity:0.6; }\n"
    ".agent-log-btn:hover { opacity:1; }\n"
    "REMOVER o event listener de click no .agent-card (que abria logs) "
    "para nao conflitar com o clique no select LLM.\n\n"

    "4. GROUPING POR TIME (JS + CSS):\n"
    "Em renderTeamDetail(), ao gerar agentsHtml, agrupar os cards por time:\n"
    "  - UPSTREAM: designer, arquiteto (mais negocios se existir)\n"
    "  - DOWNSTREAM: dev, qa\n"
    "  - coordenador fica separado, sempre no topo\n"
    "Adicionar <div class=\"team-section\"> com <h3>Team Name</h3> antes de cada grupo.\n"
    "CSS: .team-section { margin-bottom: 16px; }\n"
    ".team-section h3 { font-size:0.8rem; text-transform:uppercase; color:var(--text-secondary); margin-bottom:8px; letter-spacing:1px; }\n\n"

    "5. BUSINESS AGENT (novo agente + registro):\n"
    "Criar contexts/AFP-Team/negocios/CONTEXTO.md com:\n"
    "  Proposito: Definir prioridades de negocio, validar ROI das features, "
    "manter contato com stakeholders.\n"
    "  Acoes: analisar_mercado, definir_prioridades, validar_requisitos\n"
    "Registrar em contexts/AFP-Team/project.json como agente 'negocios' "
    "(module_path: src/agents/design_factory.py, class_name: DesignAgent, "
    "emoji: 💼, role: designer). Usar DesignAgent como fallback enquanto nao tem agente proprio.\n"
    "Criar arvore de contexto (INDEX.md + tree/) para negocios via ContextTree.\n\n"

    "6. AUDITORIA DE CONTEXTO:\n"
    "Verificar cada arvore em contexts/AFP-Team/*/tree/ e confirmar que:\n"
    "  - Os arquivos .md existem e tem conteudo\n"
    "  - O diretorio tree/ existe\n"
    "  - INDEX.md existe\n"
    "Se algum estiver vazio, significa que o post-hook nao esta persistindo. "
    "Relatar no resumo.\n\n"

    "7. DESIGNER PESQUISA:\n"
    "Delegar ao designer uma pesquisa de design systems, tendencias de UI "
    "para dashboard operacional, com foco em cards de status, hierarquia de "
    "informacao e paletas de cores para status (success, running, failed).\n\n"

    "8. PRIMEIRA PAGINA:\n"
    "Em renderProjectsView(), adicionar indicador visual se algum agente "
    "esta em execucao (running). Verificar state.agentsState e se algum "
    "tem status='running', mostrar badge '⚠️ X agents running' destacado.\n\n"

    "9. APROVEITAR ESPACO EM TELA (CSS):\n"
    "Encontrar #app ou .container ou o wrapper principal do dashboard. "
    "Aumentar max-width de 1200px para 1400px ou 90vw. "
    "Reduzir padding lateral de 32px para 16px em telas grandes.\n"
    "Isso elimina as sobras à direita e esquerda.\n\n"

    "Ordem: 1 (CSS) -> 2 (CSS) -> 3 (JS+CSS) -> 4 (JS+CSS) -> 5+6 (novo agente) -> 7 (designer) -> 8 (JS) -> 9 (CSS) -> pytest.\n"
    "Commits apos cada alteracao."
)

print(f"Executando 8 ajustes...", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective})
print(f"Status: {result['status']}", flush=True)
print(f"Steps: {result['total_steps']} OK={result['completed']} Fail={result['failed']}", flush=True)
for s in result.get("steps", []):
    ok = "OK" if s.get("decision") in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:50s} {s['agent_id']:12s} {s['status']}", flush=True)
