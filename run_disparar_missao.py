"""Trigger mission and print full result."""
import sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

import logging
logging.getLogger("pika").setLevel(logging.ERROR)

from src.mcp.server import run_objective

result = run_objective(
    project_id="AFP-Team",
    objective="Remover o Interaction Flow (timeline-panel) do Console AFP, mantendo apenas o Mission Control",
    context=(
        "Remover funcao renderTimeline(), div timeline-panel do renderTeamDetail(), "
        "CSS exclusivo do Interaction Flow. "
        "NAO remover nada do Mission Control (mission-card-v2, mc-*). "
        "Contextos dos agentes ja atualizados com instrucoes detalhadas."
    )
)

print(json.dumps(result, indent=2, ensure_ascii=False))
