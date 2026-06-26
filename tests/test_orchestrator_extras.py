"""Tests for Pipeline, ContextInjector, and LLMCache."""

import json
import time
from pathlib import Path

from src.orchestrator.pipeline import Pipeline, PipelineStep, PipelineResult
from src.orchestrator.context_injector import ContextInjector
from src.orchestrator.cache import LLMCache, CachedProvider
from src.llm import MockProvider, LLMResponse


# ─── Mock Agent ─────────────────────────────────────────────────

class MockAgent:
    def __init__(self, agent_id: str, fail: bool = False):
        self.agent_id = agent_id
        self._fail = fail
        self.calls = []

    def run(self, task: dict) -> "TaskResult":
        self.calls.append(task)
        from datetime import datetime
        from src.protocols.schema import TaskResult, AgentStatus
        now = datetime.utcnow()
        if self._fail:
            return TaskResult(
                agent_id=self.agent_id,
                project_id="test",
                task_id=task.get("task_id", "unknown"),
                status=AgentStatus.FAILED,
                started_at=now,
                completed_at=now,
                summary="Mock failure",
                output={},
            )
        return TaskResult(
            agent_id=self.agent_id,
            project_id="test",
            task_id=task.get("task_id", "unknown"),
            status=AgentStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            summary=f"Executed by {self.agent_id}",
            output={"result": f"{self.agent_id}_done"},
        )


# ─── Pipeline Tests ─────────────────────────────────────────────

class TestPipeline:
    def test_simple_pipeline(self):
        agents = {
            "worker_a": MockAgent("worker_a"),
            "worker_b": MockAgent("worker_b"),
        }
        pipeline = Pipeline([
            PipelineStep(id="step_a", agent_id="worker_a", input={"task_id": "t1"}),
            PipelineStep(id="step_b", agent_id="worker_b", input={"prev": "{step_a.output}"}),
        ])
        result = pipeline.run(agents, {"spec": "test"})
        assert result.success
        assert len(result.step_results) == 2

    def test_placeholder_resolution(self):
        agents = {"worker": MockAgent("worker")}
        pipeline = Pipeline([
            PipelineStep(id="first", agent_id="worker", input={"task_id": "t1"}, output_key="first_result"),
            PipelineStep(id="second", agent_id="worker", input={"task_id": "t2", "from_prev": "{first_result.output.result}"}),
        ])
        result = pipeline.run(agents, {})
        assert result.success
        # Second call should have resolved placeholder
        second_input = agents["worker"].calls[1]
        assert "from_prev" in second_input
        assert "worker_done" in str(second_input["from_prev"])

    def test_failure_abort(self):
        agents = {
            "good": MockAgent("good"),
            "bad": MockAgent("bad", fail=True),
            "never_called": MockAgent("never_called"),
        }
        pipeline = Pipeline([
            PipelineStep(id="s1", agent_id="good", input={"task_id": "t1"}),
            PipelineStep(id="s2", agent_id="bad", input={"task_id": "t2"}, on_failure="abort"),
            PipelineStep(id="s3", agent_id="never_called", input={"task_id": "t3"}),
        ])
        result = pipeline.run(agents, {})
        assert not result.success
        assert "s2" in result.failed_steps
        assert len(agents["never_called"].calls) == 0

    def test_failure_skip(self):
        agents = {
            "good": MockAgent("good"),
            "bad": MockAgent("bad", fail=True),
            "recovery": MockAgent("recovery"),
        }
        pipeline = Pipeline([
            PipelineStep(id="s1", agent_id="good", input={"task_id": "t1"}),
            PipelineStep(id="s2", agent_id="bad", input={"task_id": "t2"}, on_failure="skip"),
            PipelineStep(id="s3", agent_id="recovery", input={"task_id": "t3"}),
        ])
        result = pipeline.run(agents, {})
        assert not result.success
        assert "s2" in result.failed_steps
        assert len(agents["recovery"].calls) == 1

    def test_pipeline_result_duration(self):
        agents = {"w": MockAgent("w")}
        pipeline = Pipeline([PipelineStep(id="s1", agent_id="w", input={"task_id": "t1"})])
        result = pipeline.run(agents, {})
        assert result.duration_seconds >= 0
        assert isinstance(result.final_state, dict)

    def test_to_from_dict(self):
        steps = [
            {"id": "a", "agent_id": "x", "input": {"task": "test"}},
            {"id": "b", "agent_id": "y", "input": {"prev": "{a.result}"}},
        ]
        pipeline = Pipeline.from_dict(steps)
        assert len(pipeline.steps) == 2
        assert pipeline.steps[0].id == "a"
        exported = pipeline.to_dict()
        assert exported[0]["id"] == "a"


# ─── ContextInjector Tests ──────────────────────────────────────

class TestContextInjector:
    def test_select_strategy(self):
        injector = ContextInjector()
        state = {"a": 1, "b": 2, "c": 3}
        result = injector.inject(state, {"strategy": "select", "keep_keys": ["a", "c"]})
        assert result == {"a": 1, "c": 3}

    def test_drop_keys(self):
        injector = ContextInjector()
        state = {"a": 1, "b": 2, "c": 3}
        result = injector.inject(state, {"strategy": "select", "drop_keys": ["b"]})
        assert result == {"a": 1, "c": 3}

    def test_truncate_strategy(self):
        injector = ContextInjector()
        state = {"text": "x" * 10000, "meta": "short"}
        result = injector.inject(state, {"strategy": "truncate", "max_chars": 1000})
        assert len(result["text"]) < len(state["text"])
        assert result["meta"] == "short"

    def test_summarize_fallback(self):
        """Sem LLM, summarize cai para truncate."""
        injector = ContextInjector()
        state = {"text": "hello " * 500}
        result = injector.inject(state, {"strategy": "summarize", "max_chars": 500})
        assert len(result["text"]) <= 550  # truncated

    def test_summarize_with_llm(self):
        """Com MockProvider, summarize retorna summary."""
        mock = MockProvider(responses=["Contexto resumido com acordos preservados."])
        injector = ContextInjector(llm_provider=mock)
        state = {"contract": "Valor: R$ 1000", "details": "muito texto..."}
        result = injector.inject(state, {"strategy": "summarize", "max_tokens": 100})
        assert "_summary" in result
        assert result["_strategy"] == "summarize"


# ─── LLMCache Tests ─────────────────────────────────────────────

class TestLLMCache:
    def test_memory_cache_hit(self):
        cache = LLMCache(backend="memory", ttl=3600)
        messages = [{"role": "user", "content": "Hello"}]
        # No cache yet
        assert cache.get(messages, "model-x", 0.7, 100) is None
        # Set
        resp = LLMResponse(content="Hi there!", model="model-x", usage={"prompt_tokens": 5, "completion_tokens": 3}, finish_reason="stop")
        cache.set(messages, "model-x", 0.7, 100, resp)
        # Hit
        cached = cache.get(messages, "model-x", 0.7, 100)
        assert cached is not None
        assert cached.content == "Hi there!"

    def test_cache_miss_different_params(self):
        cache = LLMCache(backend="memory", ttl=3600)
        messages = [{"role": "user", "content": "Hello"}]
        resp = LLMResponse(content="Hi", model="m", usage={}, finish_reason="stop")
        cache.set(messages, "model-a", 0.7, 100, resp)
        # Different model
        assert cache.get(messages, "model-b", 0.7, 100) is None

    def test_expiry(self):
        cache = LLMCache(backend="memory", ttl=1)
        messages = [{"role": "user", "content": "Hello"}]
        resp = LLMResponse(content="Hi", model="m", usage={}, finish_reason="stop")
        cache.set(messages, "m", 0.7, 100, resp)
        assert cache.get(messages, "m", 0.7, 100) is not None
        time.sleep(1.5)
        assert cache.get(messages, "m", 0.7, 100) is None

    def test_sqlite_cache(self, tmp_path):
        db = tmp_path / "cache.db"
        cache = LLMCache(backend="sqlite", ttl=3600, db_path=db)
        messages = [{"role": "user", "content": "Persist test"}]
        resp = LLMResponse(content="Persisted!", model="m", usage={"prompt_tokens": 10, "completion_tokens": 5}, finish_reason="stop")
        cache.set(messages, "m", 0.7, 200, resp)
        cached = cache.get(messages, "m", 0.7, 200)
        assert cached is not None
        assert cached.content == "Persisted!"
        assert cached.usage.get("prompt_tokens") == 10

    def test_stats(self):
        cache = LLMCache(backend="memory", ttl=3600)
        stats = cache.stats()
        assert "entries" in stats
        assert "total_hits" in stats
        assert "total_tokens_cached" in stats

    def test_clear(self):
        cache = LLMCache(backend="memory", ttl=3600)
        messages = [{"role": "user", "content": "X"}]
        resp = LLMResponse(content="Y", model="m", usage={}, finish_reason="stop")
        cache.set(messages, "m", 0.5, 50, resp)
        assert cache.get(messages, "m", 0.5, 50) is not None
        cache.clear()
        assert cache.get(messages, "m", 0.5, 50) is None

    def test_hit_count(self):
        cache = LLMCache(backend="memory", ttl=3600)
        messages = [{"role": "user", "content": "testing"}]
        resp = LLMResponse(content="tested", model="m", usage={}, finish_reason="stop")
        cache.set(messages, "m", 0.5, 50, resp)
        cache.get(messages, "m", 0.5, 50)
        cache.get(messages, "m", 0.5, 50)
        stats = cache.stats()
        assert stats["total_hits"] >= 2


class TestCachedProvider:
    def test_cached_provider(self):
        cache = LLMCache(backend="memory", ttl=3600)
        mock = MockProvider(responses=["Response A", "Response B"])
        cached_provider = CachedProvider(mock, cache)

        # First call goes to provider
        r1 = cached_provider.chat(messages=[{"role": "user", "content": "Q"}], model="mock")
        assert r1.content == "Response A"
        assert "_cache" not in r1.usage or r1.usage.get("_cache") != "hit"

        # Second call should be cached (MockProvider would return "Response B" but cache returns "Response A")
        r2 = cached_provider.chat(messages=[{"role": "user", "content": "Q"}], model="mock")
        assert r2.content == "Response A"
        assert r2.usage.get("_cache") == "hit"
        # MockProvider was only called once
        assert mock._call_count == 1

    def test_is_available(self):
        mock = MockProvider()
        cache = LLMCache(backend="memory")
        cp = CachedProvider(mock, cache)
        assert cp.is_available()
