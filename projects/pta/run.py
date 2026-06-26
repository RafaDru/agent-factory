"""
PTA — Run Script
==================
Script para executar o projeto PTA no Agent Factory.

Arquitetura: Agent Factory é plataforma de execução.
Agentes vivem em pta-mobile/agentes/.
Factory carrega sob demanda via AgentLoader.
"""

import sys
import time
from pathlib import Path

# Adicionar raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.registry import get_registry
from src.protocols.schema import ProjectConfig


def run_pta():
    """Executa o projeto PTA com segregação completa."""
    
    print("=" * 60)
    print("Agent Factory — Projeto PTA")
    print("=" * 60)
    
    # 1. Registrar projeto PTA
    print("\n1. Registrando projeto PTA...")
    registry = get_registry()
    
    config = ProjectConfig(
        project_id="pta",
        name="Personal Trainer Agent",
        description="App mobile com IA e visao computacional",
    )
    
    project_id = registry.register(config)
    notifier = registry.get_notifier(project_id)
    
    print(f"   Projeto registrado: {project_id}")
    print(f"   Eventos em: .agent-factory/events/{project_id}/")
    
    # 2. Listar referencias de agentes
    print("\n2. Referencias de agentes:")
    refs = registry.list_agent_refs(project_id)
    for agent_id, ref in refs.items():
        print(f"   - {agent_id}: {ref.class_name} @ {ref.module_path}")
    
    # 3. Carregar agentes sob demanda
    print("\n3. Carregando agentes sob demanda:")
    agents = {}
    for agent_id in refs:
        agent = registry.load_agent(project_id, agent_id)
        agents[agent_id] = agent
        print(f"   - {agent_id} ({agent.role.value})")
    
    # Configurar subordinados do coordenador
    agents["coordenador"].set_subordinates(agents)
    
    # 4. Executar pipeline via Coordenador
    print("\n4. Executando pipeline via Coordenador...")
    
    # Coordenador delega tarefa de CV
    print("\n   [Coordenador] Delegando tarefa de CV...")
    agents["coordenador"].run({
        "task_id": "pta-orchestrated-1",
        "task_type": "cv_task",
        "payload": {
            "task_id": "cv-task-1",
            "action": "detect_pose"
        }
    })
    
    # Coordenador delega tarefa de Mobile
    print("\n   [Coordenador] Delegando tarefa de Mobile...")
    agents["coordenador"].run({
        "task_id": "pta-orchestrated-2",
        "task_type": "mobile_task",
        "payload": {
            "task_id": "mobile-task-1",
            "action": "create_component",
            "component_name": "LoginScreen"
        }
    })
    
    # Coordenador delega tarefa de UI/UX
    print("\n   [Coordenador] Delegando tarefa de UI/UX...")
    agents["coordenador"].run({
        "task_id": "pta-orchestrated-3",
        "task_type": "ui_task",
        "payload": {
            "task_id": "ui-task-1",
            "action": "create_style",
            "component": "LoginScreen"
        }
    })
    
    # Coordenador delega tarefa de QA
    print("\n   [Coordenador] Delegando tarefa de QA...")
    agents["coordenador"].run({
        "task_id": "pta-orchestrated-4",
        "task_type": "qa_task",
        "payload": {
            "task_id": "qa-task-1",
            "action": "run_tests"
        }
    })
    
    # 5. Status final
    print("\n" + "=" * 60)
    print("Status do Projeto PTA:")
    print("=" * 60)
    
    status = registry.get_project_status(project_id)
    print(f"   Projeto: {status['project_id']}")
    print(f"   Agentes: {', '.join(status['agents'])}")
    print(f"   Referencias: {', '.join(status['agent_refs'])}")
    print(f"   Total de eventos: {status['total_events']}")
    print(f"   Concluidos: {status['completed_events']}")
    print(f"   Falhas: {status['failed_events']}")
    
    # 6. Context usage
    print("\n5. Context Usage:")
    for agent_id, agent in agents.items():
        usage = agent.get_context_usage()
        print(f"   - {agent_id}: {usage['used_kb']:.1f}KB / {usage['limit_kb']:.1f}KB ({usage['percentage']:.1f}%) [{usage['status']}]")
    
    print("\nProjeto PTA executado com sucesso!")
    print(f"  Dashboard: http://localhost:8080?project={project_id}")
    
    return project_id


if __name__ == "__main__":
    run_pta()
