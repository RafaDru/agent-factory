"""
SOLARMAN Solar Monitor — Funcoes de Monitoramento
=================================================
send_weekly_report: relatorio semanal via ntfy.sh
check_panel_degradation: detecta degradacao de paineis
get_dashboard_metrics: metricas para dashboard HTML
"""

import os
import json
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
except ImportError:
    psycopg2 = None

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "solarman"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}


def get_conn():
    if psycopg2 is None:
        raise ImportError("psycopg2-binary nao instalado")
    return psycopg2.connect(**DB_CONFIG)


def send_weekly_report() -> dict[str, Any]:
    """Gera relatorio semanal de geracao e envia via ntfy.sh."""
    import requests

    since = datetime.utcnow() - timedelta(days=7)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    ROUND(SUM(ac_power) / 1000.0, 2) AS kwh_semana,
                    ROUND(AVG(ac_power), 2) AS potencia_media_w,
                    MAX(ac_power) AS pico_w,
                    COUNT(DISTINCT date_trunc('day', recorded_at)) AS dias_ativos
                FROM energia_microinversor
                WHERE recorded_at >= %s
            """, (since,))
            dados = dict(cur.fetchone())

    economia = round(dados.get("kwh_semana", 0) * 0.95, 2)
    msg = (
        f"📊 Relatorio Semanal\n"
        f"Geracao: {dados.get('kwh_semana', 0)} kWh\n"
        f"Economia: R$ {economia}\n"
        f"Potencia media: {dados.get('potencia_media_w', 0)}W\n"
        f"Pico: {dados.get('pico_w', 0)}W"
    )

    ntfy_topic = os.environ.get("NTFY_TOPIC", "solarman-alerts")
    requests.post(
        f"https://ntfy.sh/{ntfy_topic}",
        data=msg.encode("utf-8"),
        headers={"Title": "Relatorio Semanal Solar", "Tags": "sunny"},
        timeout=10,
    )

    return {"status": "ok", "dados": dados, "mensagem_enviada": True}


def check_panel_degradation() -> dict[str, Any]:
    """Analisa tendencia de degradacao nos ultimos 30 dias."""
    since = datetime.utcnow() - timedelta(days=30)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    date_trunc('day', recorded_at) AS dia,
                    MAX(ac_power) AS pico_diario
                FROM energia_microinversor
                WHERE recorded_at >= %s
                GROUP BY 1
                ORDER BY 1
            """, (since,))
            registros = [dict(r) for r in cur.fetchall()]

    if len(registros) < 7:
        return {"status": "dados_insuficientes", "dias": len(registros)}

    primeiro_pico = registros[0]["pico_diario"] or 1
    ultimo_pico = registros[-1]["pico_diario"] or 1
    degradacao = round((1 - ultimo_pico / primeiro_pico) * 100, 2)

    return {
        "status": "ok",
        "degradacao_percentual": degradacao,
        "dias_analisados": len(registros),
        "alerta": degradacao > 15,
        "primeiro_pico_w": primeiro_pico,
        "ultimo_pico_w": ultimo_pico,
    }


def get_dashboard_metrics() -> dict[str, Any]:
    """Retorna metricas resumidas para o dashboard."""
    since = datetime.utcnow() - timedelta(days=1)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    ROUND(SUM(ac_power) / 1000.0, 2) AS kwh_hoje,
                    ROUND(AVG(ac_power), 2) AS potencia_media_w,
                    MAX(ac_power) AS pico_w,
                    COUNT(DISTINCT microinversor_id) AS inversores_ativos,
                    MAX(recorded_at) AS ultima_leitura
                FROM energia_microinversor
                WHERE recorded_at >= %s
            , (since,))
            hoje = dict(cur.fetchone())

            cur.execute("""
                SELECT
                    ROUND(SUM(ac_power) / 1000.0, 2) AS kwh_total,
                    ROUND(SUM(ac_power) / 1000.0 * 0.95, 2) AS economia_total
                FROM energia_microinversor
            """)
            total = dict(cur.fetchone())

    hoje["ultima_leitura"] = hoje.get("ultima_leitura").isoformat() if hoje.get("ultima_leitura") else None
    return {
        "status": "ok",
        "hoje": hoje,
        "total": total,
        "timestamp": datetime.utcnow().isoformat(),
    }
