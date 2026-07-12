import sys, json
sys.path.insert(0, ".")

from src.registry import get_registry
from src.protocols.events import EventNotifier

registry = get_registry()
project_id = "solarman-solar-monitor"

coord = registry.load_agent(project_id, "coordenador")
subs = {}
for aid in ["negocios", "desenvolvedor", "design"]:
    subs[aid] = registry.load_agent(project_id, aid)
coord.set_subordinates(subs)

goal = """Gerar plano de implementacao para o monitor solar residencial com base na analise de negocios:

1. Performance Ratio (PR): Implementar calculo de PR movel (7 e 30 dias) no banco PostgreSQL com view materializada
2. Autoconsumo: Calcular taxa de autoconsumo diaria e mensal (% da geracao consumida localmente)
3. Assimetria entre inversores: Alertas quando diferenca de producao entre Deye MI > 5%
4. Deteccao de sujeira/degradacao: Correlacao temperatura x potencia; teste de recuperacao pos-chuva
5. Economia em R$: Calcular economia com base na tarifa CEMIG (R$ 0,88/kWh) e geracao real
6. Integracao CEMIG: View para cruzar geracao com creditos, calcular saldo e economia real"""

context = """O projeto eh 100% funcional em Python + PostgreSQL + ntfy.sh.
Usina: 3.78 kWp, 2 microinversores Deye MI, 7 paineis, Lagoa Santa MG.
Tabelas existentes: stations, devices, readings_realtime, device_readings, daily_production, alerts.
O banco ja acumula dados historicos. Precisamos de queries SQL e views, nao de novas APIs.
Stack alvo: Python + psycopg2 + SQL views + ntfy.sh para alertas."""

result = coord.run({
    "task_id": "solar-plan-001",
    "action": "plan_and_execute",
    "goal": goal,
    "context": context,
    "tasks": [
        {
            "name": "analise-tecnica",
            "agent_id": "desenvolvedor",
            "task": {
                "task_id": "dev-analise",
                "action": "analyze_code",
                "prompt": f"""Analise o codigo fonte do monitor.py e o schema.sql no diretorio C:\\Users\\rafae\\Workspace\\solarman-solar-monitor.

Contexto do projeto: {context}

Objetivos a implementar: {goal}

Para cada item, responda:
1. QUAIS arquivos precisam ser modificados ou criados
2. LOGICA necessaria (SQL queries, funcoes Python, triggers)
3. ESFORCO estimado (baixo/medio/alto)
4. DEPENDENCIAS entre os itens
5. ORDEM de implementacao recomendada

Seja tecnico e especifico. Inclua exemplos de SQL ou Python quando relevante.""",
            },
            "depends_on": [],
        },
    ],
})

output = result.output if hasattr(result, "output") else {}
print(f"\nStatus: {result.status.value}")
for step in output.get("steps", []):
    print(f"\n{'='*60}")
    print(f"PASSO: {step['step']} ({step['status']})")
    print('='*60)
    if "result" in step:
        resp = step["result"]
        if isinstance(resp, dict):
            print(resp.get("response", str(resp)[:3000]))
        else:
            print(str(resp)[:3000])
    if "error" in step:
        print(f"ERRO: {step['error']}")

print("\n\n=== CONCLUIDO ===")
