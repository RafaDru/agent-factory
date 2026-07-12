-- ===========================================================
-- SOLARMAN Solar Monitor — SQL Views para Analise
-- ===========================================================

-- 1. Performance Ratio: eficiencia do sistema ao longo do tempo
CREATE OR REPLACE VIEW v_performance_ratio AS
SELECT
    date_trunc('day', recorded_at) AS dia,
    ROUND(AVG(ac_power::numeric / NULLIF(dc_power, 0)), 4) AS performance_ratio,
    COUNT(*) AS amostras
FROM energia_microinversor
WHERE dc_power > 0
GROUP BY 1
ORDER BY 1 DESC;

-- 2. Autoconsumo: consumo vs geracao
CREATE OR REPLACE VIEW v_autoconsumo AS
SELECT
    date_trunc('day', recorded_at) AS dia,
    ROUND(AVG(potencia_atual::numeric), 2) AS consumo_medio_w,
    ROUND(AVG(ac_power::numeric), 2) AS geracao_media_w,
    ROUND(
        AVG(ac_power::numeric) / NULLIF(AVG(potencia_atual::numeric), 0) * 100,
        2
    ) AS percentual_autoconsumo
FROM energia_microinversor
WHERE recorded_at >= NOW() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1 DESC;

-- 3. Economia: economia acumulada em reais (base R$0,95/kWh)
CREATE OR REPLACE VIEW v_economia AS
SELECT
    date_trunc('month', recorded_at) AS mes,
    ROUND(SUM(ac_power::numeric) / 1000.0, 2) AS kwh_gerado,
    ROUND(SUM(ac_power::numeric) / 1000.0 * 0.95, 2) AS economia_rl,
    COUNT(DISTINCT date_trunc('day', recorded_at)) AS dias_com_dado
FROM energia_microinversor
GROUP BY 1
ORDER BY 1 DESC;

-- 4. Assimetria: alerta quando inversores tem geracao muito diferente
CREATE OR REPLACE VIEW v_assimetria_inversores AS
SELECT
    e1.recorded_at,
    e1.ac_power AS inv1_w,
    e2.ac_power AS inv2_w,
    ROUND(
        ABS(e1.ac_power - e2.ac_power) / NULLIF(GREATEST(e1.ac_power, e2.ac_power), 0) * 100,
        2
    ) AS assimetria_pct
FROM energia_microinversor e1
JOIN energia_microinversor e2
    ON e1.recorded_at = e2.recorded_at
    AND e1.microinversor_id < e2.microinversor_id
WHERE e1.ac_power > 0 AND e2.ac_power > 0
    AND recorded_at >= NOW() - INTERVAL '7 days';

-- 5. Alerta de limpeza: geracao abaixo do esperado (possivel sujeira)
CREATE OR REPLACE VIEW v_alerta_limpeza AS
WITH daily_peak AS (
    SELECT
        date_trunc('day', recorded_at) AS dia,
        MAX(ac_power) AS pico_w
    FROM energia_microinversor
    WHERE recorded_at >= NOW() - INTERVAL '14 days'
    GROUP BY 1
)
SELECT
    dia,
    pico_w,
    ROUND(
        (pico_w - LAG(pico_w) OVER (ORDER BY dia))
        / NULLIF(LAG(pico_w) OVER (ORDER BY dia), 0) * 100,
        2
    ) AS variacao_pct,
    CASE
        WHEN pico_w < LAG(pico_w) OVER (ORDER BY dia) * 0.7
        THEN 'ALERTA: possivel sujeira nos paineis'
        WHEN pico_w < LAG(pico_w) OVER (ORDER BY dia) * 0.85
        THEN 'ATENCAO: queda moderada na geracao'
        ELSE 'Normal'
    END AS recomendacao
FROM daily_peak
ORDER BY dia DESC;
