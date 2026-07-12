import sys, json
sys.path.insert(0, ".")

from src.registry import get_registry

registry = get_registry()
project_id = "solarman-solar-monitor"

# Carregar coordenador + subordinates
coord = registry.load_agent(project_id, "coordenador")
subs = {}
for aid in ["negocios", "desenvolvedor", "design"]:
    subs[aid] = registry.load_agent(project_id, aid)
coord.set_subordinates(subs)
print(f"Coordenador carregado com: {list(subs.keys())}")

print("\n>>> Executando Tarefa via Coordenador (plan_and_execute)")
print(">>> Negocios analisa oportunidades de otimizacao\n")

result = coord.run({
    "task_id": "solar-001",
    "action": "plan_and_execute",
    "goal": "Analisar oportunidades de otimizacao do monitor solar",
    "tasks": [
        {
            "name": "analise-oportunidades",
            "agent_id": "negocios",
            "task": {
                "task_id": "analise-001",
                "action": "analyze",
                "prompt": """Como especialista em energia solar residencial (Brasil, Lagoa Santa MG, CEMIG), analise:

1. TOP 5 METRICAS que um usuario residencial deve monitorar (alem de kWh gerado)
2. OPORTUNIDADES: o que mais pode ser extraido dos dados ja coletados?
3. PREVENCAO: como detectar sujeira/degradacao antes da queda brusca?
4. EXPANSAO: que dados ajudam a decidir se vale expandir ou adicionar bateria?
5. INTEGRACAO: vale a pena cruzar com dados da concessionaria?

Responda em portugues, formato estruturado com topicos e subtopicos.""",
            },
            "depends_on": [],
        },
    ],
})

output = result.output if hasattr(result, "output") else result
status = result.status.value if hasattr(result, "status") else "?"
print(f"\nStatus: {status}")
print(f"Steps: {output.get('completed', '?')}/{output.get('total_steps', '?')}")

for step in output.get("steps", []):
    print(f"\n--- {step['step']} ({step['status']}) ---")
    if "result" in step:
        resp = step["result"]
        if isinstance(resp, dict):
            print(resp.get("response", str(resp)[:500]))
        else:
            print(str(resp)[:500])
    if "error" in step:
        print(f"ERRO: {step['error']}")

print("\n=== CONCLUIDO ===")
