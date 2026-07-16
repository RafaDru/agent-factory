import sys, time
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
print("Script started", flush=True)

from src.registry import get_registry
registry = get_registry()
print("Registry loaded", flush=True)

agents = {}
for aid in ("dev", "qa", "designer", "coordenador"):
    print(f"Loading {aid}...", flush=True)
    agents[aid] = registry.load_agent("AFP-Team", aid)
    print(f"  {aid} loaded", flush=True)

coord = agents["coordenador"]
coord.set_subordinates({
    "dev": agents["dev"], "qa": agents["qa"], "designer": agents["designer"],
})
print("Coordinator configured", flush=True)

objective = (
    "Adicionar seletor de modelo LLM nos cards de agente do dashboard:\n"
    "1. No renderTeamDetail() em src/dashboard/index.html, substituir o texto 'Mode: AUTO / groq/llama-3.3-70b' "
    "por um dropdown <select> com: AUTO, opencode_zen (deepseek-v4-pro), "
    "groq (llama-3.3-70b), opencode (deepseek-v4-pro)\n"
    "2. Ao selecionar o dropdown, enviar POST /api/agent-config com agent_id e llm_provider\n"
    "3. Adicionar endpoint /api/agent-config em src/dashboard/server.py (GET + POST)\n"
    "4. Salvar config em .agent-factory/agent_config.json\n"
    "5. Carregar config salva ao iniciar o dashboard\n"
    "Use refactor_code com file_path='src/dashboard/index.html' para o HTML/JS e "
    "refactor_code com file_path='src/dashboard/server.py' para o servidor."
)

context = (
    "Ja tem painel de logs. "
    "Ja tem EventSource SSE. "
    "IMPORTANTE: arquivos sao src/dashboard/index.html e src/dashboard/server.py (NUNCA src/components/). "
    "server.py usa SimpleHTTPRequestHandler. "
    "Nao introduzir frameworks externos."
)

print(f"Executing objective ({len(objective)} chars)...", flush=True)
t0 = time.time()
result = coord.execute({"action": "plan_and_execute", "goal": objective, "context": context})
print(f"Done in {time.time()-t0:.0f}s", flush=True)
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
