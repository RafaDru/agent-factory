"""Missao: AFP-Team adiciona seletor de modelo LLM no dashboard."""
import sys, time
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
agents = {}
for aid in ("dev", "qa", "designer", "coordenador"):
    agents[aid] = registry.load_agent("AFP-Team", aid)

coord = agents["coordenador"]
coord.set_subordinates({
    "dev": agents["dev"], "qa": agents["qa"], "designer": agents["designer"],
})

objective = (
    "Adicionar seletor de modelo LLM nos cards de agente do dashboard:\n"
    "1. No renderTeamDetail() em src/dashboard/index.html, substituir 'Mode: AUTO / groq/llama-3.3-70b' "
    "por um dropdown com: AUTO, opencode_zen (deepseek-v4-pro), "
    "groq (llama-3.3-70b), opencode (deepseek-v4-pro)\n"
    "2. Ao selecionar, enviar POST /api/agent-config com agent_id e llm_provider\n"
    "3. Adicionar endpoint /api/agent-config em src/dashboard/server.py (GET + POST)\n"
    "4. Salvar config em .agent-factory/agent_config.json\n"
    "5. Carregar config salva ao iniciar\n"
    "Use refactor_code com file_path='src/dashboard/index.html' e "
    "refactor_code com file_path='src/dashboard/server.py'."
)

context = (
    "Ja tem painel de logs. "
    "Ja tem EventSource SSE. "
    "server.py usa SimpleHTTPRequestHandler. "
    "Nao introduzir frameworks externos."
)

result = coord.execute({"action": "plan_and_execute", "goal": objective, "context": context})
print(f"Status: {result['status']}")
for s in result.get("steps", []):
    d = s.get("decision","")
    ok = "OK" if d in ("accept","skip") else "XX"
    print(f"  [{ok}] {s['step']:45s} {s['agent_id']:10s} {s['status']}")
    if s.get("status") == "failure":
        res = s.get("result", {})
        if isinstance(res, dict):
            for k in ("error","rationale"):
                v = res.get(k,"")
                if v: print(f"          {k}: {str(v)[:400]}")
