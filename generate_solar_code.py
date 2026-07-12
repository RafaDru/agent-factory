import sys, json
sys.path.insert(0, ".")

from src.registry import get_registry

registry = get_registry()
project_id = "solarman-solar-monitor"
dev = registry.load_agent(project_id, "desenvolvedor")

# Step 1: Generate SQL views
result1 = dev.run({
    "task_id": "sql-views",
    "action": "implement",
    "prompt": """Gere SQL views para o schema PostgreSQL de um monitor solar residencial (3.78 kWp, 2 microinversores Deye MI, Lagoa Santa MG).

Tabelas existentes:
- daily_production(station_id, date, total_generation_kwh, total_consumption_kwh, total_purchase_kwh, total_export_kwh, peak_power_w)
- readings_realtime(station_id, recorded_at, generation_power_w, use_power_w, irradiate_intensity, total_dc_power_w, total_ac_output_w, max_inverter_temp)
- device_readings(device_id, recorded_at, dc_power_pv1..pv4, ac_output_power_w, total_production_kwh, daily_production_kwh, inverter_temp)
- devices(id, device_sn, device_type, station_id)
- stations(id, name, installed_capacity_kwp)

Gere 5 CREATE OR REPLACE VIEW statements:

1. v_performance_ratio: 
   - Junta daily_production com stations
   - PR = total_generation_kwh / (installed_capacity_kwp * peak_sun_hours)
   - peak_sun_hours estimado de irradiate_intensity em readings_realtime do dia
   - Incluir: date, station_name, generation_kwh, capacity_kwp, peak_sun_hours, performance_ratio, status (BOM se PR>0.75, REGULAR se 0.6-0.75, RUIM se <0.6)

2. v_autoconsumo:
   - Diario: taxa de autoconsumo = 1 - (total_export_kwh / total_generation_kwh) quando houver dados
   - Senao, assume 100% (residencial tipico)
   - Incluir: date, station_name, generation_kwh, export_kwh, consumo_proprio_kwh, taxa_autoconsumo_pct

3. v_economia:
   - savings_brl = total_generation_kwh * 0.88
   - Incluir: date, station_name, generation_kwh, savings_brl, savings_cumulative_brl (window sum)

4. v_assimetria_inversores:
   - Producao diaria de cada microinversor (device_type IN ('MICRO_INVERTER','INVERTER'))
   - Diferenca percentual entre o maior e menor
   - Incluir: date, device_1_sn, device_1_kwh, device_2_sn, device_2_kwh, diferenca_pct, status (OK se <5%, ATENCAO se 5-10%, CRITICO se >10%)

5. v_alerta_limpeza:
   - Detecta possivel sujeira/degradacao:
   - Alta temperatura do inversor (>65C) + baixa potencia ( <50% da nominal) = suspeita
   - Compara producao com media movel 7 dias
   - Incluir: date, device_sn, inverter_temp, ac_power_w, avg_7d_temp, avg_7d_power, ratio_temp, ratio_power, alerta_sujeira (SIM/NAO), confianca (ALTA/MEDIA/BAIXA)

Retorne APENAS os 5 blocos SQL dentro de ```sql ... ``` markers.
Cada view deve ter comentarios explicativos em portugues.
Use tabelas existentes, nao crie colunas novas.""" ,
})

output1 = result1.output if hasattr(result1, "output") else {}
sql_raw = output1.get("response", "")

# Extract SQL between ```sql markers
import re
sql_blocks = re.findall(r'```sql\s*(.*?)\s*```', sql_raw, re.DOTALL)
if not sql_blocks:
    sql_blocks = re.findall(r'```\s*(.*?)\s*```', sql_raw, re.DOTALL)
    sql_blocks = [b for b in sql_blocks if b.strip().upper().startswith("CREATE")]

sql_code = "\n\n".join(sql_blocks) if sql_blocks else sql_raw
print(f"SQL gerado: {len(sql_code)} chars, {len(sql_blocks)} blocos extraidos")

if sql_blocks:
    for i, block in enumerate(sql_blocks, 1):
        name_match = re.search(r'(?:CREATE OR REPLACE\s+)?VIEW\s+(\w+)', block, re.IGNORECASE)
        name = name_match.group(1) if name_match else f"bloco_{i}"
        lines = block.strip().split('\n')
        print(f"  {name}: {len(lines)} linhas")

# Step 2: Generate Python functions
result2 = dev.run({
    "task_id": "py-funcs",
    "action": "implement",
    "prompt": """Gere funcoes Python para adicionar ao monitor.py de um monitor solar residencial.

O monitor.py atual tem:
- send_daily_summary(conn, station_name): envia resumo diario via ntfy.sh
- send_alert(alert_title, message): envia alerta via ntfy.sh
- check_generation_failure(now, state_file, station_id): alerta 24h sem geracao
- Importacoes: psycopg2, psycopg2.extras, requests, os, datetime, json
- Tabelas: stations, devices, readings_realtime, device_readings, daily_production, alerts

Gere 3 funcoes:

1. send_weekly_report(conn):
   - Query views v_performance_ratio, v_economia, v_autoconsumo, v_assimetria_inversores
   - Agregar dados da ultima semana (7 dias)
   - Calcular: producao total, PR medio, economia R$, assimetria maxima
   - Enviar via ntfy.sh com formato bonito (usar emojis)
   - Se assimetria > 5%, incluir alerta

2. check_panel_degradation(conn, station_id):
   - Query v_alerta_limpeza para hoje
   - Se alerta_sujeira = 'SIM' e confianca = 'ALTA', enviar alerta
   - Inserir alerta na tabela alerts

3. get_dashboard_metrics(conn):
   - Query todas as views para o dia/mes atual
   - Retornar dict com: {today_kwh, month_kwh, today_pr, avg_pr, month_savings, total_savings, assimetria_pct, alerta_limpeza}
   - Nao enviar notificacao, apenas retornar dados

Cada funcao deve ter docstring em portugues.
Use conn ou cur como parametro de conexao.
Retorne APENAS o codigo Python em blocos ```python.

Requisitos:
- Usar psycopg2.extras.RealDictCursor para queries mais legiveis
- Tratar erros com try/except
- Nao quebrar funcoes existentes""",
})

output2 = result2.output if hasattr(result2, "output") else {}
py_raw = output2.get("response", "")

py_blocks = re.findall(r'```python\s*(.*?)\s*```', py_raw, re.DOTALL)
if not py_blocks:
    py_blocks = re.findall(r'```\s*(.*?)\s*```', py_raw, re.DOTALL)
    py_blocks = [b for b in py_blocks if 'def ' in b]

py_code = "\n\n".join(py_blocks) if py_blocks else py_raw
print(f"\nPython gerado: {len(py_code)} chars, {len(py_blocks)} blocos extraidos")

if py_blocks:
    for i, block in enumerate(py_blocks, 1):
        func_match = re.search(r'def\s+(\w+)\s*\(', block)
        name = func_match.group(1) if func_match else f"bloco_{i}"
        lines = block.strip().split('\n')
        print(f"  {name}: {len(lines)} linhas")

# Save to temp files for inspection
with open(r"C:\Users\rafae\agent-factory\.generated_views.sql", "w", encoding="utf-8") as f:
    f.write(f"-- SQL Views geradas pelo DesenvolvedorAgent em {__import__('datetime').datetime.now():%Y-%m-%d %H:%M}\n\n")
    f.write(sql_code)

with open(r"C:\Users\rafae\agent-factory\.generated_functions.py", "w", encoding="utf-8") as f:
    f.write(f"# Funcoes Python geradas pelo DesenvolvedorAgent em {__import__('datetime').datetime.now():%Y-%m-%d %H:%M}\n\n")
    f.write(py_code)

print(f"\nArquivos salvos em:")
print(f"  .generated_views.sql ({len(sql_code)} chars)")
print(f"  .generated_functions.py ({len(py_code)} chars)")
print("\n=== CONCLUIDO ===")
