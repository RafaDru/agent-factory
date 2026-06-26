"""
Agent Factory — Pipeline com Cache e Context Injection
========================================================
Demonstra o uso combinado de Pipeline, ContextInjector e LLMCache.

Fluxo:
  1. Code → Gera código Python via SubprocessAgent
  2. QA → Testa o código via SubprocessAgent
  3. Review → Revisa resultado via LLM (cacheado)
  4. Context injector entre cada passo comprime/selciona o estado
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator.pipeline import Pipeline, PipelineStep
from src.orchestrator.cache import LLMCache, CachedProvider
from src.orchestrator.context_injector import ContextInjector
from src.llm import MockProvider


def main():
    # Cache SQLite para evitar chamadas LLM repetidas
    cache = LLMCache(backend="memory", ttl=3600)
    llm = CachedProvider(MockProvider(responses=[
        "Código revisado. Aprovado.",
    ]), cache)

    # Context injector com sumarização
    injector = ContextInjector(llm_provider=llm)

    # Mock agents (substitua por SubprocessAgent/LLMAgent reais)
    class FakeAgent:
        def __init__(self, name):
            self.name = name
        def run(self, task):
            from datetime import datetime
            from src.protocols.schema import TaskResult, AgentStatus
            now = datetime.utcnow()
            print(f"  [{self.name}] Executando: {task.get('task_id')}")
            return TaskResult(
                agent_id=self.name, project_id="demo",
                task_id=task.get("task_id", "?"),
                status=AgentStatus.COMPLETED,
                started_at=now, completed_at=now,
                summary=f"{self.name} OK",
                output={"result": f"{self.name}_done", "code": "print('hello')"},
            )

    agents = {
        "code": FakeAgent("code"),
        "qa": FakeAgent("qa"),
        "review": FakeAgent("review"),
    }

    # Pipeline: Code → QA → Review
    pipeline = Pipeline([
        PipelineStep(
            id="codegen",
            agent_id="code",
            input={"task_id": "gen-1", "spec": "{input.spec}"},
            output_key="code_output",
            inject={"strategy": "select", "keep_keys": ["input"]},
        ),
        PipelineStep(
            id="qa_test",
            agent_id="qa",
            input={"task_id": "qa-1", "code": "{codegen.output.result}"},
            output_key="qa_output",
            inject={"strategy": "truncate", "max_chars": 500},
        ),
        PipelineStep(
            id="review",
            agent_id="review",
            input={"task_id": "rv-1", "qa_result": "{qa_test.output.result}"},
            on_failure="skip",
        ),
    ], context_injector=injector)

    print("Executando pipeline: Code >> QA >> Review\n")
    result = pipeline.run(agents, {"spec": "Criar função de soma"})

    print(f"\nPipeline {'OK sucesso' if result.success else 'FALHA'}")
    print(f"Passos executados: {len(result.step_results)}")
    print(f"Passos com falha: {result.failed_steps or 'nenhum'}")
    print(f"Duration: {result.duration_seconds:.2f}s")

    # Cache stats
    cache_stats = cache.stats()
    print(f"\nCache: {cache_stats['entries']} entradas, {cache_stats['total_hits']} hits")


if __name__ == "__main__":
    main()
