import sys
sys.path.insert(0, ".")

from src.registry import get_registry

registry = get_registry()

for aid in ["coordenador", "negocios", "desenvolvedor", "design"]:
    try:
        agent = registry.load_agent("solarman-solar-monitor", aid)
        caps = agent.get_capabilities()
        print(f"{aid}: OK role={caps['role']} actions={list(caps.get('actions', {}).keys())}")
    except Exception as e:
        print(f"{aid}: FAIL {e}")
