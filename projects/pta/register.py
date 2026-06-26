"""
PTA — Personal Trainer Agent
==============================
Configuração do projeto PTA no Agent Factory.
"""

import sys
from pathlib import Path

# Adicionar raiz do agent-factory ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.registry import get_registry
from src.protocols.schema import ProjectConfig


def register_pta_project() -> str:
    """
    Registra o projeto PTA no Agent Factory.
    
    Returns:
        project_id registrado
    """
    registry = get_registry()
    
    config = ProjectConfig(
        project_id="pta",
        name="Personal Trainer Agent",
        description="App mobile com IA e visão computacional para correção de exercícios",
    )
    
    project_id = registry.register(config)
    
    print(f"* Projeto PTA registrado: {project_id}")
    print(f"  - Eventos em: .agent-factory/events/{project_id}/")
    print(f"  - Config em: .agent-factory/projects/{project_id}/")
    
    return project_id


if __name__ == "__main__":
    register_pta_project()
