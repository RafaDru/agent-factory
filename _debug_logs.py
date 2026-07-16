import sys; sys.path.insert(0, '.')
from src.registry import get_registry
agents = {}
for aid in ("dev", "qa", "coordenador"):
    agents[aid] = get_registry().load_agent("AFP-Team", aid)
coord = agents["coordenador"]
coord.set_subordinates({"dev": agents["dev"], "qa": agents["qa"]})

r = coord.execute({
    "action": "plan_and_execute",
    "goal": "Corrigir painel de logs. Envolver o segundo <script> em DOMContentLoaded.",
    "context": "src/dashboard/index.html ~1665 linhas."
})
for s in r.get("steps", []):
    print(f"{s.get('step','?')} ({s.get('agent_id','?')}) status={s.get('status','?')}")
    res = s.get("result", {})
    if isinstance(res, dict):
        for k in ("error","rationale"):
            v = res.get(k,"")
            if v: print(f"  {k}: {str(v)[:400]}")
