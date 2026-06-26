"""
Teste simples do AgentLoader
"""

import sys
from pathlib import Path

# Adicionar caminho do agent-factory ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loader import AgentLoader, AgentReference
from src.registry import ProjectRegistry
from src.protocols.schema import ProjectConfig
from src.protocols.events import EventNotifier


def test_agent_reference():
    """Testa criação de referência."""
    ref = AgentReference(
        agent_id="test-agent",
        module_path="C:/Users/rafae/PersonalTrainerAgent/agentes",
        class_name="QAAgent",
        context_file="C:/Users/rafae/PersonalTrainerAgent/agentes/qa/CONTEXTO.md",
        context_limit_kb=8.0,
    )
    
    assert ref.agent_id == "test-agent"
    assert ref.class_name == "QAAgent"
    assert ref.context_limit_kb == 8.0
    
    # Serialização
    data = ref.to_dict()
    assert data["agent_id"] == "test-agent"
    
    # Deserialização
    ref2 = AgentReference.from_dict(data)
    assert ref2.agent_id == ref.agent_id
    assert ref2.class_name == ref.class_name
    
    print("[OK] AgentReference")


def test_agent_loader():
    """Testa carregamento de agente."""
    loader = AgentLoader()
    
    ref = AgentReference(
        agent_id="qa",
        module_path="C:/Users/rafae/PersonalTrainerAgent/agentes",
        class_name="QAAgent",
        context_file="C:/Users/rafae/PersonalTrainerAgent/agentes/qa/CONTEXTO.md",
        context_limit_kb=8.0,
    )
    
    notifier = EventNotifier("test-project")
    
    agent = loader.load(ref, project_id="test-project", notifier=notifier)
    
    assert agent.agent_id == "qa"
    assert agent._context_manager.limit_kb == 8.0
    assert agent._context_manager.context_file is not None
    
    print("[OK] AgentLoader")


def test_registry_with_refs():
    """Testa registry com referências."""
    registry = ProjectRegistry(base_dir=".agent-factory-test")
    
    # Registrar projeto
    config = ProjectConfig(
        project_id="test",
        name="Test Project",
    )
    registry.register(config)
    
    # Adicionar referência
    ref = AgentReference(
        agent_id="qa",
        module_path="C:/Users/rafae/PersonalTrainerAgent/agentes",
        class_name="QAAgent",
    )
    registry.add_agent_ref("test", ref)
    
    # Verificar referência
    loaded_ref = registry.get_agent_ref("test", "qa")
    assert loaded_ref is not None
    assert loaded_ref.agent_id == "qa"
    
    # Carregar agente
    agent = registry.load_agent("test", "qa")
    assert agent.agent_id == "qa"
    
    print("[OK] Registry with refs")


if __name__ == "__main__":
    test_agent_reference()
    test_agent_loader()
    test_registry_with_refs()
    print("\n[SUCCESS] Todos os testes passaram!")
