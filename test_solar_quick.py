import sys, json
sys.path.insert(0, ".")

from src.registry import get_registry

registry = get_registry()
project_id = "solarman-solar-monitor"

print("Carregando NegociosAgent...")
agent = registry.load_agent(project_id, "negocios")
print(f"OK: {agent.get_capabilities()['actions'].keys()}")

print("\nExecutando analise rapida...")
result = agent.run({
    "task_id": "quick-test",
    "action": "analyze",
    "prompt": "Liste 3 metricas principais que um dono de usina solar residencial deveria monitorar diariamente. Responda em portugues, formato lista simples.",
})

output = result.output if hasattr(result, "output") else result
print(f"\nStatus: {result.status.value}")
if isinstance(output, dict):
    resp = output.get("response", str(output))
    print(resp[:1000])
else:
    print(str(output)[:1000])
