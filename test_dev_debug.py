import sys, json
sys.path.insert(0, ".")

from src.registry import get_registry

registry = get_registry()
project_id = "solarman-solar-monitor"

coord = registry.load_agent(project_id, "coordenador")
subs = {}
for aid in ["negocios", "desenvolvedor", "design"]:
    subs[aid] = registry.load_agent(project_id, aid)
coord.set_subordinates(subs)

# Test just the implement action directly on desenvolvedor
dev = subs["desenvolvedor"]

result = dev.run({
    "task_id": "dev-test",
    "action": "implement",
    "prompt": "Gere uma view SQL chamada v_economia que calcula economia em R$ multiplicando geracao_kwh * 0.88. A view deve usar a tabela daily_production. Retorne APENAS o SQL em blocos ```sql.",
})

output = result.output if hasattr(result, "output") else {}
print(f"Status: {result.status.value}")
resp = output.get("response", "")
print(f"Response length: {len(resp)} chars")
print(resp[:2000])
