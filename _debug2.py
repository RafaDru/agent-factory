import sys, json; sys.path.insert(0, '.')
from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
agents = {}
for aid in ("dev", "qa", "coordenador"):
    agents[aid] = registry.load_agent("AFP-Team", aid)
coord = agents["coordenador"]
coord.set_subordinates({"dev": agents["dev"], "qa": agents["qa"]})

f1 = (
    "Adicionar toggle light/dark mode no dashboard (src/dashboard/index.html):\n"
    "No <style> final (antes de </style>), adicionar:\n"
    "  :root[data-theme='dark'] com cores atuais\n"
    "  :root[data-theme='light'] com fundo #f8f9fa, texto #1a1a2e, cards #fff\n"
    "No <header> .header-actions, adicionar botao toggle (lua/sol)\n"
    "No <script> final (antes de </script>), adicionar toggleTheme() + localStorage\n"
    "Use refactor_code."
)

r = coord.execute({"action": "plan_and_execute", "goal": f1, "context": "src/dashboard/index.html ~1400 linhas"})
print("Status:", r["status"])
for s in r.get("steps", []):
    print(f"\n--- {s.get('step','?')} ({s.get('agent_id','?')}) ---")
    print(f"  status: {s.get('status','')}  decision: {s.get('decision','')}")
    rat = s.get("rationale","") or ""
    if rat:
        print(f"  rationale: {rat[:600]}")
    res = s.get("result","") or ""
    if isinstance(res, dict):
        for k in ("error","rationale","status","summary"):
            v = res.get(k,"")
            if v:
                print(f"  result.{k}: {str(v)[:600]}")
    elif res:
        print(f"  result: {str(res)[:600]}")
