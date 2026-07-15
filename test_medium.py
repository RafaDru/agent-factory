"""
Test: more complex objective that's similar to the bug fix mission.
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.as_posix())

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
if not registry.project_exists("AFP-Team"):
    registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

agents = {}
for aid in ("dev", "qa", "coordenador"):
    agent = registry.load_agent("AFP-Team", aid)
    agents[aid] = agent

coord = agents["coordenador"]
coord.set_subordinates({
    "dev": agents["dev"],
    "qa": agents["qa"],
})

# Medium complexity objective
objective = (
    "Read the file src/dashboard/index.html and find all places where "
    "the JavaScript references 'project.name', 'project.id', 'agent.id', or 'project.teams'. "
    "The API returns 'project_name', 'project_id', 'agent_id' and no 'teams' array. "
    "List the line numbers and the old/new values needed."
)

print(f"Objective: {len(objective)} chars")
sys.stdout.flush()

try:
    result = coord.execute({
        "action": "plan_and_execute",
        "goal": objective,
        "context": "The file is ~1388 lines of HTML+JS.",
    })
    print(f"Status: {result['status']}")
    print(f"Steps: {result['total_steps']} completed={result['completed']} failed={result['failed']}")
    for s in result.get("steps", []):
        print(f"  [{s['agent_id']:10s}] {s['step']:40s} {s['status']}")
    sys.stdout.flush()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
