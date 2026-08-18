"""
Testes do AgentLoader e registry com agentes declarativos da plataforma.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loader import AgentLoader, AgentReference
from src.registry import ProjectRegistry
from src.protocols.schema import ProjectConfig
from src.protocols.events import EventNotifier

ROOT = Path(__file__).parent.parent
WORKER_MODULE = str(ROOT / "src" / "agents" / "worker.py")
DEV_CONFIG = str(ROOT / "src" / "agents" / "configs" / "dev.json")


def test_agent_reference():
    """Testa criacao de referencia."""
    ref = AgentReference(
        agent_id="test-agent",
        module_path=WORKER_MODULE,
        class_name="DeclarativeWorker",
        context_file=str(ROOT / "contexts" / "demo-onboarding" / "dev" / "CONTEXTO.md"),
        context_limit_kb=8.0,
    )

    assert ref.agent_id == "test-agent"
    assert ref.class_name == "DeclarativeWorker"
    assert ref.context_limit_kb == 8.0

    data = ref.to_dict()
    assert data["agent_id"] == "test-agent"

    ref2 = AgentReference.from_dict(data)
    assert ref2.agent_id == ref.agent_id
    assert ref2.class_name == ref.class_name


def test_agent_loader():
    """Testa carregamento de DeclarativeWorker."""
    loader = AgentLoader()

    ref = AgentReference(
        agent_id="dev",
        module_path=WORKER_MODULE,
        class_name="DeclarativeWorker",
        context_file=str(ROOT / "contexts" / "demo-onboarding" / "dev" / "CONTEXTO.md"),
        context_limit_kb=8.0,
    )

    notifier = EventNotifier("test-project")

    agent = loader.load(ref, project_id="test-project", notifier=notifier)

    assert agent.agent_id == "dev"
    assert agent._context_manager.limit_kb == 8.0


def test_registry_with_refs():
    """Testa registry com referencias."""
    registry = ProjectRegistry(base_dir=".agent-factory-test")

    config = ProjectConfig(
        project_id="test",
        name="Test Project",
    )
    registry.register(config)

    ref = AgentReference(
        agent_id="dev",
        module_path=WORKER_MODULE,
        class_name="DeclarativeWorker",
        context_file=str(ROOT / "contexts" / "demo-onboarding" / "dev" / "CONTEXTO.md"),
    )
    registry.add_agent_ref("test", ref)

    loaded_ref = registry.get_agent_ref("test", "dev")
    assert loaded_ref is not None
    assert loaded_ref.agent_id == "dev"

    agent = registry.load_agent("test", "dev")
    assert agent.agent_id == "dev"


if __name__ == "__main__":
    test_agent_reference()
    test_agent_loader()
    test_registry_with_refs()
