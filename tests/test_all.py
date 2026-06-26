"""
Agent Factory — Tests
=====================
Testes unitários para o framework.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path

# Adicionar raiz ao path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.protocols.schema import AgentEvent, AgentStatus, AgentRole, TaskResult, ProjectConfig
from src.protocols.events import EventNotifier
from src.agents.base import AgentBase, CoordinatorAgent
from src.agents.real import SubprocessAgent, LLMAgent
from src.persistence import ContextStore
from src.llm import MockProvider, LLMResponse


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_dir():
    """Cria diretório temporário para testes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def notifier(temp_dir):
    """Cria EventNotifier para testes."""
    return EventNotifier("test-project", output_dir=temp_dir)


@pytest.fixture
def mock_provider():
    """Cria MockProvider para testes."""
    return MockProvider(responses=["Resposta 1", "Resposta 2"])


# ─── Schema Tests ────────────────────────────────────────────────────────────

class TestAgentEvent:
    def test_create_event(self):
        event = AgentEvent(
            agent_id="test-agent",
            agent_role=AgentRole.WORKER,
            status=AgentStatus.RUNNING,
            task_id="task-1",
            project_id="test-project",
            message="Testando",
        )
        
        assert event.agent_id == "test-agent"
        assert event.status == AgentStatus.RUNNING
        assert event.project_id == "test-project"
        assert event.event_id is not None
        assert event.trace_id is not None
    
    def test_event_with_payload(self):
        payload = {"key": "value", "count": 42}
        event = AgentEvent(
            agent_id="test-agent",
            agent_role=AgentRole.WORKER,
            status=AgentStatus.COMPLETED,
            task_id="task-1",
            project_id="test-project",
            message="Concluído",
            payload=payload,
        )
        
        assert event.payload == payload
    
    def test_event_serialization(self):
        event = AgentEvent(
            agent_id="test-agent",
            agent_role=AgentRole.WORKER,
            status=AgentStatus.RUNNING,
            task_id="task-1",
            project_id="test-project",
        )
        
        # Serializar para JSON
        data = event.model_dump(mode="json")
        assert "agent_id" in data
        assert "timestamp" in data
        
        # Deserializar
        event2 = AgentEvent.model_validate(data)
        assert event2.agent_id == event.agent_id


class TestTaskResult:
    def test_create_result(self):
        now = datetime.utcnow()
        result = TaskResult(
            task_id="task-1",
            agent_id="test-agent",
            project_id="test-project",
            status=AgentStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            output={"result": "ok"},
            summary="Tarefa concluída",
        )
        
        assert result.task_id == "task-1"
        assert result.status == AgentStatus.COMPLETED
        assert result.output == {"result": "ok"}


class TestProjectConfig:
    def test_create_config(self):
        config = ProjectConfig(
            project_id="my-project",
            name="Meu Projeto",
            description="Descrição do projeto",
        )
        
        assert config.project_id == "my-project"
        assert config.max_retries == 3
        assert config.timeout_seconds == 3600


# ─── EventNotifier Tests ─────────────────────────────────────────────────────

class TestEventNotifier:
    def test_emit_event(self, notifier):
        event = AgentEvent(
            agent_id="test-agent",
            agent_role=AgentRole.WORKER,
            status=AgentStatus.RUNNING,
            task_id="task-1",
            project_id="test-project",
            message="Testando",
        )
        
        notifier.emit(event)
        
        # Verificar que o arquivo foi criado
        assert notifier._events_file.exists()
        
        # Verificar que o evento foi salvo
        events = notifier.get_events()
        assert len(events) == 1
        assert events[0].agent_id == "test-agent"
    
    def test_get_status(self, notifier):
        status = notifier.get_status()
        assert "phase" in status
        assert "progress" in status
    
    def test_get_events_empty(self, notifier):
        events = notifier.get_events()
        assert len(events) == 0


# ─── AgentBase Tests ─────────────────────────────────────────────────────────

class SimpleAgent(AgentBase):
    """Agente simples para testes."""
    
    def validate_input(self, task):
        return "data" in task
    
    def execute(self, task):
        return {"result": f"Processado: {task['data']}"}


class FailingAgent(AgentBase):
    """Agente que falha sempre."""
    
    def validate_input(self, task):
        return True
    
    def execute(self, task):
        raise RuntimeError("Erro simulado")


class TestAgentBase:
    def test_agent_run_success(self, notifier):
        agent = SimpleAgent("simple", "test", notifier)
        
        result = agent.run({
            "task_id": "task-1",
            "data": "teste",
        })
        
        assert result.status == AgentStatus.COMPLETED
        assert result.output == {"result": "Processado: teste"}
        assert result.total_duration_ms > 0
    
    def test_agent_run_failure(self, notifier):
        agent = FailingAgent("failing", "test", notifier)
        
        result = agent.run({
            "task_id": "task-2",
        })
        
        assert result.status == AgentStatus.FAILED
        assert result.output == {}
        # O erro é emitido como evento, não armazenado no TaskResult
        # Verificar que eventos de falha foram emitidos
        events = notifier.get_events()
        failed_events = [e for e in events if e.status == AgentStatus.FAILED]
        assert len(failed_events) > 0
        assert "Erro simulado" in failed_events[0].error
    
    def test_agent_validation_failure(self, notifier):
        agent = SimpleAgent("simple", "test", notifier)
        
        # Tarefa sem campo "data" — validação deve falhar
        result = agent.run({
            "task_id": "task-3",
        })
        
        assert result.status == AgentStatus.FAILED
    
    def test_agent_events_emitted(self, notifier):
        agent = SimpleAgent("simple", "test", notifier)
        
        agent.run({
            "task_id": "task-4",
            "data": "teste",
        })
        
        events = notifier.get_events()
        # Deve ter: RUNNING (início), RUNNING (validado), COMPLETED (fim)
        assert len(events) >= 2


# ─── CoordinatorAgent Tests ──────────────────────────────────────────────────

class ConcreteCoordinator(CoordinatorAgent):
    """Coordenador concreto para testes."""
    
    def validate_input(self, task):
        return True
    
    def execute(self, task):
        # Delega para o primeiro worker registrado
        if self._workers:
            worker_id = list(self._workers.keys())[0]
            return self.delegate(task, worker_id).output
        return {}


class TestCoordinatorAgent:
    def test_register_worker(self, notifier):
        coord = ConcreteCoordinator("coord", "test", notifier)
        worker = SimpleAgent("worker-1", "test", notifier)
        
        coord.register_worker(worker)
        assert "worker-1" in coord._workers
    
    def test_delegate_task(self, notifier):
        coord = ConcreteCoordinator("coord", "test", notifier)
        worker = SimpleAgent("worker-1", "test", notifier)
        coord.register_worker(worker)
        
        result = coord.delegate({
            "task_id": "task-1",
            "data": "teste",
        }, "worker-1")
        
        assert result.status == AgentStatus.COMPLETED
        assert result.output == {"result": "Processado: teste"}
    
    def test_delegate_to_unknown_worker(self, notifier):
        coord = ConcreteCoordinator("coord", "test", notifier)
        
        with pytest.raises(ValueError, match="não registrado"):
            coord.delegate({
                "task_id": "task-1",
                "data": "teste",
            }, "unknown-worker")


# ─── SubprocessAgent Tests ───────────────────────────────────────────────────

class TestSubprocessAgent:
    def test_execute_code(self, notifier):
        agent = SubprocessAgent("executor", "test", notifier)
        
        result = agent.run({
            "task_id": "task-1",
            "code": "print('Olá mundo')",
        })
        
        assert result.status == AgentStatus.COMPLETED
        assert "Olá mundo" in result.output["stdout"]
        assert result.output["success"] is True
    
    def test_execute_code_with_args(self, notifier):
        agent = SubprocessAgent("executor", "test", notifier)
        
        result = agent.run({
            "task_id": "task-2",
            "code": "print(args['name'])",
            "args": {"name": "Rafael"},
        })
        
        assert result.status == AgentStatus.COMPLETED
        assert "Rafael" in result.output["stdout"]
    
    def test_execute_failing_code(self, notifier):
        agent = SubprocessAgent("executor", "test", notifier)
        
        result = agent.run({
            "task_id": "task-3",
            "code": "raise ValueError('Erro de teste')",
        })
        
        assert result.status == AgentStatus.COMPLETED  # Subprocess rodou
        assert result.output["success"] is False
        assert "Erro de teste" in result.output["stderr"]
    
    def test_execute_script(self, notifier, temp_dir):
        # Criar script temporário
        script_path = Path(temp_dir) / "test_script.py"
        script_path.write_text("print('Script executado')", encoding="utf-8")
        
        agent = SubprocessAgent("executor", "test", notifier, working_dir=temp_dir)
        
        result = agent.run({
            "task_id": "task-4",
            "script": str(script_path),
        })
        
        assert result.status == AgentStatus.COMPLETED
        assert "Script executado" in result.output["stdout"]


# ─── LLMAgent Tests ──────────────────────────────────────────────────────────

class TestLLMAgent:
    def test_llm_chat(self, notifier, mock_provider):
        agent = LLMAgent(
            "analyst",
            "test",
            notifier,
            provider=mock_provider,
            system_prompt="Você é um analista.",
        )
        
        result = agent.run({
            "task_id": "task-1",
            "prompt": "Analise estes dados",
        })
        
        assert result.status == AgentStatus.COMPLETED
        assert result.output["response"] == "Resposta 1"
        assert result.output["model"] == "mock-model"
    
    def test_llm_with_context(self, notifier, mock_provider):
        agent = LLMAgent(
            "analyst",
            "test",
            notifier,
            provider=mock_provider,
        )
        
        result = agent.run({
            "task_id": "task-2",
            "prompt": "Continue a análise",
            "context": {"previous_analysis": "dados anteriores"},
        })
        
        assert result.status == AgentStatus.COMPLETED
        # Verificar que o contexto foi passado
        assert len(mock_provider.history) == 1
        messages = mock_provider.history[0]["messages"]
        assert len(messages) == 3  # system + context + user


# ─── ContextStore Tests ──────────────────────────────────────────────────────

class TestContextStore:
    def test_save_and_get_agent_context(self, temp_dir):
        store = ContextStore("test", db_dir=temp_dir)
        
        store.save_agent_context("agent-1", {"last_task": "task-1", "count": 5})
        context = store.get_agent_context("agent-1")
        
        assert context["last_task"] == "task-1"
        assert context["count"] == 5
    
    def test_save_and_get_task_context(self, temp_dir):
        store = ContextStore("test", db_dir=temp_dir)
        
        store.save_task_context("task-1", {"status": "in_progress", "data": [1, 2, 3]})
        context = store.get_task_context("task-1")
        
        assert context["status"] == "in_progress"
        assert context["data"] == [1, 2, 3]
    
    def test_get_agent_history(self, temp_dir):
        store = ContextStore("test", db_dir=temp_dir)
        
        # Criar eventos
        for i in range(5):
            event = AgentEvent(
                agent_id="agent-1",
                agent_role=AgentRole.WORKER,
                status=AgentStatus.COMPLETED,
                task_id=f"task-{i}",
                project_id="test",
                message=f"Evento {i}",
            )
            store.save_event(event)
        
        history = store.get_agent_history("agent-1", limit=3)
        assert len(history) == 3
    
    def test_get_stats(self, temp_dir):
        store = ContextStore("test", db_dir=temp_dir)
        
        # Criar alguns resultados
        for i in range(3):
            result = TaskResult(
                task_id=f"task-{i}",
                agent_id="agent-1",
                project_id="test",
                status=AgentStatus.COMPLETED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            store.save_task_result(result)
        
        stats = store.get_stats()
        assert stats["total_tasks"] == 3
        assert stats["completed_tasks"] == 3
        assert stats["success_rate"] == 100.0


# ─── MockProvider Tests ──────────────────────────────────────────────────────

class TestMockProvider:
    def test_mock_chat(self):
        provider = MockProvider(responses=["Olá", "Mundo"])
        
        response1 = provider.chat([{"role": "user", "content": "Teste 1"}])
        response2 = provider.chat([{"role": "user", "content": "Teste 2"}])
        response3 = provider.chat([{"role": "user", "content": "Teste 3"}])
        
        assert response1.content == "Olá"
        assert response2.content == "Mundo"
        assert response3.content == "Olá"  # Cicla
    
    def test_mock_is_available(self):
        provider = MockProvider()
        assert provider.is_available() is True
    
    def test_mock_history(self):
        provider = MockProvider()
        
        provider.chat([{"role": "user", "content": "Teste"}])
        
        assert len(provider.history) == 1
        assert provider.history[0]["messages"][0]["content"] == "Teste"
