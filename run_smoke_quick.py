"""Quick smoke: load coordinator and run get_capabilities (no LLM needed)"""
import sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from src.registry import get_registry

registry = get_registry()
agent = registry.load_agent("AFP-Team", "coordenador")
print(f"✅ Coordenador loaded: {type(agent).__name__}")

task = {"task_id": "smoke-001", "action": "get_capabilities"}
result = agent.run(task)
print(f"📋 Status: {result.status.value}")
out = result.output or {}
if isinstance(out, dict):
    actions = out.get("actions", out)
    print(f"📋 Actions: {list(actions.keys()) if isinstance(actions, dict) else str(actions)[:200]}")
else:
    print(f"📋 Output: {str(out)[:300]}")
print("---SMOKE_OK---")
