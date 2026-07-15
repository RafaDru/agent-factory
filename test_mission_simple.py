"""
Missao: AFP-Team corrige os bugs do dashboard (com debug).
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.as_posix())

print("[DEBUG] Starting mission script...")
sys.stdout.flush()

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

print("[DEBUG] Registry loaded")
sys.stdout.flush()

registry = get_registry()
if not registry.project_exists("AFP-Team"):
    registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))
print("[DEBUG] Registry configured")
sys.stdout.flush()

print("[DEBUG] Loading agents...")
sys.stdout.flush()

agents = {}
for aid in ("dev", "qa", "coordenador"):
    print(f"  Loading {aid}...")
    sys.stdout.flush()
    agent = registry.load_agent("AFP-Team", aid)
    agents[aid] = agent
    llm = type(agent._llm).__name__ if getattr(agent, '_llm', None) else 'NONE'
    print(f"  {aid}: {type(agent).__name__} [{llm}]")
    sys.stdout.flush()

coord = agents["coordenador"]
coord.set_subordinates({
    "dev": agents["dev"],
    "qa": agents["qa"],
})
print("[DEBUG] Agents ready")
sys.stdout.flush()

objective = "Reply with the word OK. Do not do anything else."

print("[DEBUG] Calling coord.execute with simple objective...")
sys.stdout.flush()

try:
    result = coord.execute({
        "action": "plan_and_execute",
        "goal": objective,
        "context": "Just say OK.",
    })
    print(f"[DEBUG] Result: {json.dumps(result, indent=2, default=str)[:500]}")
    sys.stdout.flush()
except Exception as e:
    print(f"[DEBUG] ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
