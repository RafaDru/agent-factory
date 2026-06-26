"""
Agent Factory — Teste com Dashboard
=====================================
Script para testar o dashboard com o projeto PTA.

Arquitetura: Agent Factory é plataforma de execução.
Agentes vivem em pta-mobile/agentes/.
Factory carrega sob demanda via AgentLoader.
"""

import sys
import time
from pathlib import Path

# Adicionar raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.registry import get_registry
from src.protocols.schema import ProjectConfig
from src.dashboard.server import DashboardServer


def run_with_dashboard():
    """Executa o projeto PTA com dashboard em tempo real."""
    
    print("=" * 60)
    print("Agent Factory — Teste com Dashboard")
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
    
    # 2. Criar e iniciar dashboard
    print("\n2. Iniciando dashboard...")
    from src.persistence import ContextStore
    store = ContextStore(project_id)
    server = DashboardServer(notifier, port=8080, context_store=store)
    server.start()
    
    print("   Dashboard: http://localhost:8080?project=pta")
    
    # 3. Carregar agentes sob demanda
    print("\n3. Carregando agentes sob demanda:")
    refs = registry.list_agent_refs(project_id)
    agents = {}
    for agent_id in refs:
        agent = registry.load_agent(project_id, agent_id)
        agents[agent_id] = agent
        print(f"   - {agent_id}")
    
    # Configurar subordinados do coordenador
    agents["coordenador"].set_subordinates(agents)
    
    # 4. Executar pipeline
    print("\n4. Executando pipeline...")
    
    tarefas = [
        ("cv_task", {"task_id": "cv-1", "action": "detect_pose"}),
        ("mobile_task", {"task_id": "mobile-1", "action": "create_component", "component_name": "PoseViewer"}),
        ("ui_task", {"task_id": "ui-1", "action": "create_style", "component": "PoseViewer"}),
        ("qa_task", {"task_id": "qa-1", "action": "run_tests"}),
    ]
    
    for task_type, payload in tarefas:
        print(f"\n   [Coordenador] Delegando {task_type}...")
        result = agents["coordenador"].run({
            "task_id": f"orchestrated-{task_type}",
            "task_type": task_type,
            "payload": payload,
        })
        time.sleep(1)
    
    # 5. Status final
    print("\n" + "=" * 60)
    print("Pipeline concluido!")
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
    
    print("\n   Dashboard ainda rodando em http://localhost:8080?project=pta")
    print("   Pressione Ctrl+C para encerrar.")
    
    # Manter rodando
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando...")
        server.stop()


if __name__ == "__main__":
    run_with_dashboard()
