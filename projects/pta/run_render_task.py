"""
PTA — Runner da Tarefa de Renderização 3D
=========================================
Delega a tarefa de renderização para o Coordenador via Agent Factory.

Arquitetura: Agent Factory é plataforma de execução.
Agentes vivem em pta-mobile/agentes/.
Factory carrega sob demanda via AgentLoader.
"""

import sys
from pathlib import Path

# Adicionar raiz do agent-factory ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.registry import get_registry


def run_task():
    # 1. Obter registro
    registry = get_registry()
    project_id = "pta"
    
    if not registry.project_exists(project_id):
        print("Projeto não registrado. Registrando...")
        from src.protocols.schema import ProjectConfig
        registry.register(ProjectConfig(
            project_id=project_id,
            name="Personal Trainer Agent",
        ))
    
    # 2. Carregar agentes sob demanda
    refs = registry.list_agent_refs(project_id)
    agents = {}
    for agent_id in refs:
        agents[agent_id] = registry.load_agent(project_id, agent_id)
    
    agents["coordenador"].set_subordinates(agents)
    
    # 3. Delegar tarefa ao Coordenador
    print("\n   [Coordenador] Delegando tarefa de renderização 3D...")
    
    task = {
        "task_id": "render-3d-test-1",
        "task_type": "render_task",
        "payload": {
            "task_id": "render-3d-1",
            "action": "render_3d_comparative",
            "input_path": "C:/Users/rafae/PersonalTrainerAgent/docs/testes/evidencias/calibragem/whatsapp/pta_video3_agachamento_whatsapp.mp4",
            "output_path": "C:/Users/rafae/PersonalTrainerAgent/docs/testes/evidencias/calibragem/calibracao/video3_3d_comparative_agent.mp4"
        }
    }
    
    result = agents["coordenador"].run(task)
    
    print(f"\nResultado da tarefa: {result.status.value}")
    print(f"Output: {result.output}")


if __name__ == "__main__":
    run_task()
