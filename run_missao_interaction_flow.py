"""Trigger mission: Remove Interaction Flow, keep only Mission Control."""
import sys, json, warnings, io
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

# Suppress noisy logs
import logging
logging.basicConfig(level=logging.WARNING)

from src.mcp.server import run_objective

print("=" * 60)
print("MISSAO: Remover Interaction Flow")
print("=" * 60)

result = run_objective(
    project_id="AFP-Team",
    objective="Remover o Interaction Flow (timeline-panel) do Console AFP, mantendo apenas o Mission Control como interface de visualizacao de missoes e eventos.",
    context=(
        "O dashboard em src/dashboard/index.html possui duas areas de visualizacao de eventos:\n"
        "1. Interaction Flow (timeline-panel) — arvore hierarquica de eventos ao lado dos agentes\n"
        "2. Mission Control — cards de missao com tasks, status, cadeia de delegacao\n\n"
        "O Interaction Flow e redundante. Remova-o completamente:\n"
        "- Remover funcao renderTimeline() e auxiliares internas (renderNode)\n"
        "- Remover div timeline-panel do renderTeamDetail()\n"
        "- Remover CSS exclusivo: .timeline-panel, .timeline-header, .node-header, .node-body, .node-footer, .mission-card (antigo), .mission-header, .mission-title, .mission-status, .mission-body, .agent-node, .execution-card\n"
        "- NAO remover nada do Mission Control (mission-card-v2, mc-*, mc-task-*)\n"
        "- NAO remover funcionalidades de navegacao por abas\n\n"
        "Contextos dos agentes ja foram atualizados com instrucoes detalhadas.\n"
        "Ordem: consultar negocios -> designer -> arquiteto -> dev -> qa"
    )
)

status = result.get("status", "?")
summary = result.get("summary", result.get("output", str(result)[:300]))
print(f"\nStatus: {status}")
print(f"Resumo: {str(summary)[:500]}")
if result.get("error_type"):
    print(f"ERRO: {result['error_type']}: {result.get('message','')}")
print("=" * 60)
