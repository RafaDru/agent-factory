"""Smoke E-012: valida RPC coordinator->runtime, eventos e missao."""
import json
import logging
import sys
import time
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.getLogger("pika").setLevel(logging.ERROR)

from src.mcp.server import run_objective

OBJECTIVE = (
    "Smoke test operacional E-012: delegar UMA tarefa ao agente dev — "
    "ler o arquivo docs/backlog.md com read_file e retornar os nomes dos "
    "3 primeiros epicos prioritarios (E-012, E-013, E-010). "
    "Nao editar nenhum arquivo."
)
CONTEXT = (
    "Missao automatizada de validacao pos-fix. Plano minimo: 1 step, agent dev, "
    "action read_file, file_path docs/backlog.md. Confirmar que RPC retorna."
)


def fetch_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 60)
    print("SMOKE E-012 — run_objective demo-onboarding")
    print("=" * 60)

    events_before = 0
    try:
        payload = fetch_json("http://127.0.0.1:8080/api/events?limit=5")
        events_before = payload.get("total", len(payload.get("events", [])))
        print(f"Eventos antes: {events_before}")
    except Exception as e:
        print(f"Aviso: dashboard events indisponivel: {e}")

    t0 = time.time()
    print("\nDisparando missao...")
    result = run_objective(
        project_id="demo-onboarding",
        objective=OBJECTIVE,
        context=CONTEXT,
    )
    elapsed = time.time() - t0
    print(f"\nConcluido em {elapsed:.1f}s")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:4000])

    status = result.get("status") or result.get("output", {}).get("status")
    mission_id = result.get("output", {}).get("mission_id") or result.get("mission_id")
    print(f"\nStatus final: {status}")
    if mission_id:
        print(f"Mission ID: {mission_id}")

    # Verificar eventos via API
    try:
        payload = fetch_json("http://127.0.0.1:8080/api/events?limit=20")
        events = payload.get("events", [])
        total = payload.get("total", len(events))
        print(f"\nEventos apos missao: {total} (delta +{total - events_before})")
        recent = events[:5]
        for ev in recent:
            print(
                f"  - {ev.get('agent_id')} | {ev.get('status')} | "
                f"{(ev.get('message') or '')[:80]}"
            )
    except Exception as e:
        print(f"Falha ao ler eventos: {e}")

    # Verificar missions API
    try:
        missions = fetch_json("http://127.0.0.1:8080/api/missions")
        items = missions.get("missions", missions) if isinstance(missions, dict) else missions
        if isinstance(items, list) and items:
            latest = items[0]
            print(
                f"\nUltima missao API: {latest.get('id')} | "
                f"status={latest.get('status')} | {latest.get('objective','')[:60]}"
            )
    except Exception as e:
        print(f"Falha ao ler missions: {e}")

    ok = str(status).lower() in ("completed", "ok", "partial", "success")
    print("\n" + ("SMOKE_OK" if ok else "SMOKE_FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
