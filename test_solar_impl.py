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

goal = """O agente de negocios ja analisou o monitor solar e identificou 6 areas de melhoria.
O desenvolvedor ja fez a analise tecnica. Agora e hora de IMPLEMENTAR.

Tarefas concretas para IMPLEMENTAR no monitor.py e schema.sql:

1. VIEW v_performance_ratio: Calcular PR diario = geracao_real_kwh / (capacidade_kwp * irradiacao_estimada_horas)
2. VIEW v_autoconsumo: Calcular consumo proprio = geracao - exportacao (ou 100% se sem medidor)
3. VIEW v_economia: Economia R$ = geracao_kwh * 0.88
4. VIEW v_assimetria: Diferenca de producao entre os 2 microinversores Deye
5. VIEW v_alerta_limpeza: Correlacao temperatura x potencia para detectar sujeira
6. Funcao Python send_weekly_report(): Relatorio semanal via ntfy.sh com as metricas acima"""

context = """Diretorio do projeto: C:/Users/rafae/Workspace/solarman-solar-monitor
Arquivos: monitor.py (codigo principal), schema.sql (schema PostgreSQL)
Banco: PostgreSQL local em 127.0.0.1:5432, database solarman, user postgres
Notificacao: ntfy.sh via NTFY_TOPIC
As views devem ser adicionadas ao schema.sql. As funcoes Python ao monitor.py.
Nao precisa testar (banco pode nao estar acessivel agora), apenas gerar o codigo."""

result = coord.run({
    "task_id": "solar-impl-001",
    "action": "plan_and_execute",
    "goal": goal,
    "context": context,
    "tasks": [
        {
            "name": "implementar-views",
            "agent_id": "desenvolvedor",
            "task": {
                "task_id": "impl-views",
                "action": "implement",
                "prompt": f"""Gere o codigo SQL completo para adicionar as seguintes views no schema.sql existente em C:\\Users\\rafae\\Workspace\\solarman-solar-monitor\\schema.sql:

1. v_performance_ratio: PR = geracao_total_kwh / (3.78 kWp * horas_sol_equivalentes)
   - Use irradiate_intensity de readings_realtime para calcular horas_sol
   - PR = daily_generation / (capacity_kwp * peak_sun_hours)
   
2. v_autoconsumo: taxa de autoconsumo diaria
   - Sem medidor de exportacao, assuma use_power_w para estimar
   
3. v_economia: economia em R$ = geracao_kwh * 0.88
   - Incluir coluna savings_brl, savings_month_brl, savings_total_brl
   
4. v_assimetria: diferenca entre os 2 microinversores
   - JOIN device_readings com devices, GROUP BY recorded_at
   - Calcular diferenca_percentual entre os 2 Deye MI
   
5. v_alerta_limpeza: identificar possivel sujeira/degradacao
   - Alta temperatura + baixa potencia = suspeita
   - Comparar com media movel de 7 dias

Retorne APENAS o SQL (CREATE OR REPLACE VIEW) pronto para executar.
Cada view deve ter comentarios explicativos em portugues.""",
            },
            "depends_on": [],
        },
        {
            "name": "implementar-relatorio",
            "agent_id": "desenvolvedor",
            "task": {
                "task_id": "impl-relatorio",
                "action": "implement",
                "prompt": f"""Gere codigo Python para adicionar ao monitor.py em C:\\Users\\rafae\\Workspace\\solarman-solar-monitor\\monitor.py:

Uma funcao send_weekly_report(conn) que:
1. Consulta as views criadas (v_performance_ratio, v_autoconsumo, v_economia, v_assimetria)
2. Calcula:
   - Producao da semana (kWh)
   - PR medio da semana
   - Economia em R$ na semana e no mes
   - Diferenca entre os 2 inversores (se > 5%, alerta)
3. Envia notificacao via ntfy.sh com formato legivel

E uma funcao send_daily_alert_v2(conn) melhorada que:
1. Verifica PR do dia vs media movel 30 dias
2. Se PR < 70%, alerta "Possivel sujeira/degradacao nos paineis"
3. Se diferenca entre inversores > 5%, alerta "Assimetria entre microinversores detectada"

Retorne APENAS o codigo Python pronto para adicionar ao monitor.py.
Use psycopg2.extras para dicionarios. Inclua docstrings.""",
            },
            "depends_on": ["implementar-views"],
        },
    ],
})

output = result.output if hasattr(result, "output") else {}
print(f"Status: {result.status.value}")
print(f"Steps: {output.get('completed', '?')}/{output.get('total_steps', '?')}")
for step in output.get("steps", []):
    print(f"\n{'='*60}")
    print(f"  {step['step']} ({step['status']})")
    print('='*60)
    if "result" in step:
        resp = step["result"]
        if isinstance(resp, dict):
            content = resp.get("response", str(resp))
            # Only show first 500 chars of code/response
            lines = content.split('\n')
            print('\n'.join(lines[:50]))
            if len(lines) > 50:
                print(f"... (mais {len(lines)-50} linhas)")
        else:
            print(str(resp)[:1500])
    if "error" in step:
        print(f"ERRO: {step['error']}")

print("\n\n=== CONCLUIDO ===")
