"""Avaliacao de qualidade LLM — missao curta com acao LLM-native."""
import json
import logging
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.getLogger("pika").setLevel(logging.ERROR)

from src.mcp.server import run_objective
from src.agents.llm_config import load_agent_llm_provider


def probe_provider(name: str) -> dict:
    from src.llm import get_provider

    t0 = time.time()
    try:
        p = get_provider(name)
        if not p.is_available():
            return {"provider": name, "ok": False, "error": "indisponivel"}
        r = p.chat(
            messages=[
                {"role": "user", "content": "Responda apenas: OK"},
            ],
            max_tokens=16,
            temperature=0,
        )
        return {
            "provider": name,
            "ok": True,
            "model": r.model,
            "latency_s": round(time.time() - t0, 2),
            "content": (r.content or "")[:80],
        }
    except Exception as e:
        return {"provider": name, "ok": False, "error": str(e), "latency_s": round(time.time() - t0, 2)}


def main():
    print("=" * 60)
    print("AVALIACAO LLM AFP-Team")
    print("=" * 60)

    for aid in ("coordenador", "dev", "arquiteto", "negocios"):
        print(f"  {aid}: {load_agent_llm_provider(aid)}")

    flash = probe_provider("opencode:deepseek-v4-flash")
    print("\nProbe opencode:deepseek-v4-flash:", json.dumps(flash, ensure_ascii=False))

    if not flash.get("ok"):
        print("ABORT: provider indisponivel")
        return 1

    objective = (
        "Avaliacao LLM: uma tarefa para arquiteto — action analyze_project "
        "com path src/agents com foco em llm_config.py. Retornar exatamente "
        "3 bullet points markdown com observacoes arquiteturais concretas. "
        "Nao editar arquivos."
    )
    context = "Plano com 1 step. Agente arquiteto. Usar analyze_project."

    t0 = time.time()
    result = run_objective(project_id="AFP-Team", objective=objective, context=context)
    elapsed = time.time() - t0

    out = result.get("output") or {}
    steps = out.get("steps") or []
    step = steps[0] if steps else {}
    details = step.get("result") or {}
    summary = details.get("summary") or details.get("rationale") or str(details)[:500]

    print(f"\nMissao em {elapsed:.1f}s status={result.get('status')} mission_status={out.get('mission_status')}")
    print("Resumo step:", summary[:800])

    ok = out.get("mission_status") == "completed" and len(summary) > 80
    if "needs_direction" in str(details).lower() or "nao definida" in summary.lower():
        ok = False

    print("\nEVAL_OK" if ok else "EVAL_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
