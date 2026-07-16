"""
Missao: AFP-Team corrige painel de logs que nao abre ao clicar.
"""
import sys
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
agents = {}
for aid in ("dev", "qa", "coordenador"):
    agents[aid] = registry.load_agent("AFP-Team", aid)

coord = agents["coordenador"]
coord.set_subordinates({"dev": agents["dev"], "qa": agents["qa"]})

objective = (
    "Corrigir painel de logs no dashboard que nao abre ao clicar no botao Logs.\n\n"

    "PROBLEMA: O segundo bloco <script> (linha ~1529 de src/dashboard/index.html) "
    "roda ANTES do HTML do painel de logs (linha ~1644). "
    "document.getElementById('logs-panel') retorna null, entao o addEventListener "
    "nunca e registrado no botao. O painel fica oculto para sempre.\n\n"

    "SOLUCAO: Envolver o segundo bloco <script> em DOMContentLoaded. "
    "Assim ele executa DEPOIS que todo o HTML (incluindo logs-panel) for carregado.\n"
    "Nao mover o bloco — apenas adicionar:\n"
    "  document.addEventListener('DOMContentLoaded', function() {\n"
    "    ... codigo existente ...\n"
    "  });\n\n"

    "TAREFAS:\n"
    "1. DEV: Usar refactor_code para src/dashboard/index.html — "
    "mover o bloco <script>(function(){...})()</script> (de ~1529 ate ~1641) "
    "para depois do </div> de logs-panel (~1662). "
    "Preservar todo o conteudo do script, apenas mover de lugar.\n"
    "2. DEV: git add + commit.\n"
    "3. QA: revisar e validar que o painel abre."
)

context = "src/dashboard/index.html ~1665 linhas. Logs panel div com id='logs-panel'."

print(f"Delegando correcao do painel de logs...", flush=True)
result = coord.execute({"action": "plan_and_execute", "goal": objective, "context": context})
print(f"Status: {result['status']}", flush=True)
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:45s} {s['agent_id']:10s} {s['status']}", flush=True)
