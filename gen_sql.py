import sys, json, re
sys.path.insert(0, ".")

from src.registry import get_registry

registry = get_registry()
project_id = "solarman-solar-monitor"
dev = registry.load_agent(project_id, "desenvolvedor")

result = dev.run({
    "task_id": "sql-views",
    "action": "implement",
    "prompt": """Gere 5 CREATE OR REPLACE VIEW statements SQL para PostgreSQL de um monitor solar.

Tabelas existentes:
- daily_production(station_id, date, total_generation_kwh, total_consumption_kwh, total_purchase_kwh, total_export_kwh, peak_power_w)
- readings_realtime(station_id, recorded_at, generation_power_w, use_power_w, irradiate_intensity)
- device_readings(device_id, recorded_at, dc_power_pv1, dc_power_pv2, dc_power_pv3, dc_power_pv4, ac_output_power_w, total_production_kwh, daily_production_kwh, inverter_temp)
- devices(id, device_sn, device_type, station_id)
- stations(id, name, installed_capacity_kwp)

Views:

1. v_performance_ratio: date, station_name, generation_kwh, capacity_kwp, irradiate_avg, performance_ratio
   PR = total_generation_kwh / (installed_capacity_kwp * peak_sun_hours)
   peak_sun_hours = SUM(irradiate_intensity)/1000 no dia (de readings_realtime)
   status_label = CASE: >0.75 'BOM', 0.6-0.75 'REGULAR', <0.6 'RUIM'

2. v_autoconsumo: date, station_name, generation_kwh, export_kwh, consumo_proprio_kwh, taxa_autoconsumo
   Se total_export_kwh > 0: taxa = 1 - (total_export_kwh / total_generation_kwh)
   Senao: taxa = 1.0 (residencial tipico sem medidor)

3. v_economia: date, station_name, generation_kwh, savings_brl, savings_cumulative_brl
   savings_brl = total_generation_kwh * 0.88
   savings_cumulative_brl = SUM(savings_brl) OVER (ORDER BY date)

4. v_assimetria_inversores: date, device_1_sn, device_1_kwh, device_2_sn, device_2_kwh, diferenca_pct, status
   Producao diaria de devices com device_type='INVERTER' ou 'MICRO_INVERTER'
   Pivot dos 2 devices para comparar lado a lado
   diferenca_pct = ABS(device_1_kwh - device_2_kwh) / GREATEST(device_1_kwh, device_2_kwh) * 100
   status = CASE: <5 'OK', 5-10 'ATENCAO', >10 'CRITICO'

5. v_alerta_limpeza: date, device_sn, inverter_temp, ac_power_w, avg_temp_7d, avg_power_7d, temp_ratio, power_ratio, alerta
   Compara leitura atual com media movel 7 dias
   Se inverter_temp > 65 OR (temp_ratio > 1.15 AND power_ratio < 0.7): alerta = 'SIM'
   alerts = 'NAO' caso contrario

Retorne APENAS os blocos SQL em ```sql ... ```.
Cada view com comentarios em portugues.
NAO crie colunas alem das listadas.
NAO use tabelas que nao existem.""",
})

output = result.output if hasattr(result, "output") else {}
sql_raw = output.get("response", "")
print(f"SQL RAW length: {len(sql_raw)}")
print("="*40)
print(sql_raw[:2000])

sql_blocks = re.findall(r'```sql\s*(.*?)\s*```', sql_raw, re.DOTALL)
if not sql_blocks:
    sql_blocks = re.findall(r'```\s*(.*?)\s*```', sql_raw, re.DOTALL)

if sql_blocks:
    sql_code = "\n\n".join(sql_blocks)
    with open(r"C:\Users\rafae\agent-factory\.generated_views.sql", "w", encoding="utf-8") as f:
        f.write("-- Views geradas pelo DesenvolvedorAgent\n\n")
        f.write(sql_code)
    print(f"\nSalvo: .generated_views.sql ({len(sql_code)} chars, {len(sql_blocks)} blocos)")
    for i, block in enumerate(sql_blocks, 1):
        m = re.search(r'VIEW\s+(\w+)', block, re.IGNORECASE)
        n = m.group(1) if m else f"bloco_{i}"
        print(f"  {i}. {n}: {len(block.strip().split(chr(10)))} linhas")
else:
    print("Nenhum bloco SQL extraido")
    with open(r"C:\Users\rafae\agent-factory\.generated_views_raw.txt", "w", encoding="utf-8") as f:
        f.write(sql_raw)
    print("Raw salvo em .generated_views_raw.txt")
