import sys, json, re
sys.path.insert(0, ".")

from src.registry import get_registry

registry = get_registry()
project_id = "solarman-solar-monitor"
dev = registry.load_agent(project_id, "desenvolvedor")

all_views = []

# Batch 1: v_performance_ratio e v_economia
r1 = dev.run({
    "task_id": "sql-1",
    "action": "implement",
    "prompt": """Gere APENAS 2 CREATE OR REPLACE VIEW para PostgreSQL.

Tabela: daily_production(station_id, date, total_generation_kwh, total_consumption_kwh, total_purchase_kwh, total_export_kwh, peak_power_w)
Tabela: readings_realtime(station_id, recorded_at, generation_power_w, use_power_w, irradiate_intensity)
Tabela: stations(id, name, installed_capacity_kwp)

VIEW 1 - v_performance_ratio:
Colunas: date, station_name, generation_kwh, capacity_kwp, irradiate_avg, peak_sun_hours, performance_ratio, status
- Junta daily_production com stations
- irradiate_avg = media diaria de irradiate_intensity de readings_realtime
- peak_sun_hours = irradiate_avg / 1000
- performance_ratio = total_generation_kwh / (installed_capacity_kwp * peak_sun_hours)
- status = CASE: >0.75 'BOM', >=0.6 'REGULAR', ELSE 'RUIM'

VIEW 2 - v_economia:
Colunas: date, station_name, generation_kwh, savings_brl, savings_cumulative_brl
- savings_brl = total_generation_kwh * 0.88
- savings_cumulative_brl = SUM(savings_brl) OVER (ORDER BY date)

Use LEFT JOIN para readings_realtime (pode nao ter dados de irradiancia todo dia).
Se peak_sun_hours for 0 ou NULL, use 5 como fallback.

Retorne APENAS ```sql ... ``` com as 2 views.""",
})
o1 = r1.output if hasattr(r1, "output") else {}
t1 = o1.get("response", "")
print(f"Batch 1: {len(t1)} chars")
sql_blocks = re.findall(r'```(?:sql)?\s*(.*?)\s*```', t1, re.DOTALL)
if sql_blocks:
    for b in sql_blocks:
        all_views.append(b.strip())
else:
    all_views.append(t1.strip())

# Batch 2: v_autoconsumo e v_assimetria
r2 = dev.run({
    "task_id": "sql-2",
    "action": "implement",
    "prompt": """Gere APENAS 2 CREATE OR REPLACE VIEW para PostgreSQL.

Tabela: daily_production(station_id, date, total_generation_kwh, total_consumption_kwh, total_purchase_kwh, total_export_kwh, peak_power_w)
Tabela: device_readings(device_id, recorded_at, dc_power_pv1, dc_power_pv2, dc_power_pv3, dc_power_pv4, ac_output_power_w, total_production_kwh, daily_production_kwh, inverter_temp)
Tabela: devices(id, device_sn, device_type, station_id)
Tabela: stations(id, name, installed_capacity_kwp)

VIEW 3 - v_autoconsumo:
Colunas: date, station_name, generation_kwh, export_kwh, consumo_proprio_kwh, taxa_autoconsumo_pct
- Se total_export_kwh > 0: consumo_proprio = generation - export, taxa = consumo / generation
- Senao: consumo_proprio = generation, taxa = 100%

VIEW 4 - v_assimetria_inversores:
Colunas: date, device_1_sn, device_1_kwh, device_2_sn, device_2_kwh, diferenca_pct, status
- Producao diaria de devices onde device_type = 'INVERTER' ou 'MICRO_INVERTER'
- Usa daily_production_kwh de device_readings, agrupado por date e device_id
- Pivot para mostrar 2 devices lado a lado
- diferenca_pct = ABS(a-b)/GREATEST(a,b)*100
- status = CASE: <5 'OK', 5-10 'ATENCAO', >10 'CRITICO'

Retorne APENAS ```sql ... ``` com as 2 views.""",
})
o2 = r2.output if hasattr(r2, "output") else {}
t2 = o2.get("response", "")
print(f"Batch 2: {len(t2)} chars")
sql_blocks = re.findall(r'```(?:sql)?\s*(.*?)\s*```', t2, re.DOTALL)
if sql_blocks:
    for b in sql_blocks:
        all_views.append(b.strip())
else:
    all_views.append(t2.strip())

# Batch 3: v_alerta_limpeza
r3 = dev.run({
    "task_id": "sql-3",
    "action": "implement",
    "prompt": """Gere 1 CREATE OR REPLACE VIEW para PostgreSQL.

Tabela: device_readings(device_id, recorded_at, dc_power_pv1, dc_power_pv2, dc_power_pv3, dc_power_pv4, ac_output_power_w, total_production_kwh, daily_production_kwh, inverter_temp)
Tabela: devices(id, device_sn, device_type, station_id)

VIEW 5 - v_alerta_limpeza:
Colunas: date, device_sn, inverter_temp, ac_power_w, avg_temp_7d, avg_power_7d, temp_ratio, power_ratio, alerta
- Para cada device, calcula a leitura mais recente do dia vs media dos ultimos 7 dias
- avg_temp_7d: media de inverter_temp nos 7 dias anteriores (mesma hora +/- 30min)
- avg_power_7d: media de ac_output_power_w nos 7 dias anteriores
- temp_ratio = inverter_temp / avg_temp_7d (se avg_temp_7d > 0)
- power_ratio = ac_output_power_w / avg_power_7d (se avg_power_7d > 0)
- alerta = CASE: inverter_temp > 65 OU (temp_ratio > 1.15 E power_ratio < 0.7) ENTAO 'SIM' SENAO 'NAO'

Use window functions LAG/AVG com frame de 7 dias.
Retorne APENAS ```sql ... ``` com a view.
NAO use tabelas alem das listadas acima.""",
})
o3 = r3.output if hasattr(r3, "output") else {}
t3 = o3.get("response", "")
print(f"Batch 3: {len(t3)} chars")
sql_blocks = re.findall(r'```(?:sql)?\s*(.*?)\s*```', t3, re.DOTALL)
if sql_blocks:
    for b in sql_blocks:
        all_views.append(b.strip())
else:
    all_views.append(t3.strip())

# Save all SQL
sql_final = "\n\n-- ============================================\n\n".join(all_views)
with open(r"C:\Users\rafae\agent-factory\.generated_views.sql", "w", encoding="utf-8") as f:
    f.write("-- Views geradas pelo DesenvolvedorAgent\n\n")
    f.write(sql_final)

print(f"\nTotal: {len(all_views)} views, {len(sql_final)} chars")
for i, v in enumerate(all_views, 1):
    m = re.search(r'VIEW\s+(\w+)', v, re.IGNORECASE)
    n = m.group(1) if m else f"view_{i}"
    print(f"  {i}. {n}: {len(v.split(chr(10)))} linhas, {len(v)} chars")
print("\n=== CONCLUIDO ===")
