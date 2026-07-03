"""
Agent Factory — Exemplo: Squad Multi-Model Local
=================================================
Demonstra o MultiModelProvider orquestrando 4 modelos locais
com cache, pipeline DAG, e contexto gerenciado.

Requer: Ollama rodando com os modelos:
  - gemma3:4b, qwen2.5-coder:7b, gemma4, qwen3.6

Uso:
    python examples/local_multi_model_squad.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm import get_provider
from src.orchestrator.cache import LLMCache, CachedProvider
from src.orchestrator.pipeline import Pipeline, PipelineStep
from src.protocols.events import EventNotifier
from src.agents.real import LLMAgent


def main():
    print("=" * 60)
    print("Agent Factory — Squad Multi-Model Local")
    print("=" * 60)

    # 1. Notifier compartilhado
    notifier = EventNotifier("squad-local")

    # 2. Cache SQLite persistente
    cache = LLMCache(backend="sqlite", ttl=86400)
    print(f"\n[Cache] Backend: {cache.backend}, TTL: {cache.ttl}s")

    # 3. MultiModelProvider via factory (get_provider("local_multi"))
    raw = get_provider("local_multi")
    provider = CachedProvider(raw, cache)
    print(f"[MultiModel] Modelos: {list(raw.capabilities.keys())}")
    print(f"[MultiModel] Classificador: {raw.classifier_model}")
    print(f"[MultiModel] Default: {raw.default_model}")

    # 4. Pipeline com 3 steps
    pipe = Pipeline("ciclo-dev-local")
    pipe.add_step(PipelineStep(
        step_id="analisar",
        description="Analisa requisitos e decide o que fazer",
        task_template={
            "prompt": (
                "Analise o contexto do projeto Agent Factory e sugira "
                "uma melhoria simples de código. "
                "Responda com: descricao, arquivo_alvo, tipo (test/code/docs)"
            ),
            "task_type": "reasoner",
        },
        input_mapping={},
    ))
    pipe.add_step(PipelineStep(
        step_id="implementar",
        description="Implementa a sugestão usando o coder especialista",
        task_template={
            "prompt": (
                "Implemente a seguinte melhoria: {analisar.response}\n"
                "Gere apenas o código, sem explicações."
            ),
            "task_type": "coder",
        },
        input_mapping={"analisar": "analisar"},
    ))
    pipe.add_step(PipelineStep(
        step_id="validar",
        description="Valida a implementação",
        task_template={
            "prompt": (
                "Revise esta implementação e aponte problemas:\n{implementar.response}"
            ),
            "task_type": "validator",
        },
        input_mapping={"implementar": "implementar"},
    ))

    # 5. Agentes registrados (cada um com seu papel)
    agents = {
        "analyst": LLMAgent(
            agent_id="analyst",
            project_id="squad-local",
            notifier=notifier,
            provider=provider,
            system_prompt="Você é um arquiteto de software experiente.",
        ),
        "developer": LLMAgent(
            agent_id="developer",
            project_id="squad-local",
            notifier=notifier,
            provider=provider,
            system_prompt="Você é um desenvolvedor senior focado em código limpo.",
        ),
        "reviewer": LLMAgent(
            agent_id="reviewer",
            project_id="squad-local",
            notifier=notifier,
            provider=provider,
            system_prompt="Você é um revisor de código exigente.",
        ),
    }

    print(f"\n[Agentes] {list(agents.keys())}")
    print(f"\n[Pipeline] Steps: {[s.step_id for s in pipe.steps]}")

    # 6. Executa o pipeline
    context = pipe.get_context()

    for step in pipe.steps:
        print(f"\n{'─' * 50}")
        print(f"[Step] {step.step_id}: {step.description}")

        task = step.build_task(context)
        if task is None:
            print("[Skip] step pulado (condição não atendida)")
            continue

        task_type = task.pop("task_type", None)
        if task_type:
            task["provider_hint"] = task_type

        agent_id = {
            "reasoner": "analyst",
            "coder": "developer",
            "validator": "reviewer",
        }.get(task_type, "analyst")

        agent = agents[agent_id]

        print(f"  Agent: {agent_id} ({task_type})")
        print(f"  Prompt: {task['prompt'][:80]}...")

        result = agent.run(task)

        status_icon = "✅" if result.status.name == "COMPLETED" else "❌"
        print(f"  {status_icon} Status: {result.status.name}")
        print(f"  ⏱  Duration: {result.total_duration_ms:.0f}ms")

        output = result.output or {}
        response_text = output.get("response", "") or output.get("stdout", "")
        context.add_result(step.step_id, response_text[:200])
        print(f"  Resposta: {response_text[:120]}...")

    # 7. Estatísticas
    stats = cache.stats()
    print(f"\n{'=' * 60}")
    print(f"[Cache] Entradas: {stats['entries']}, Hits: {stats['total_hits']}")
    print(f"[Cache] Tokens cacheados: ~{stats['total_tokens_cached']}")

    events = notifier.get_events()
    comp_duration = sum(
        e.metrics.get("duration_seconds", 0) for e in events
    )
    print(f"[Eventos] Total: {len(events)}, Duração acumulada: {comp_duration:.1f}s")
    print(f"[Pipeline] Resultado: {pipe.get_result()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
