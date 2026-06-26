"""
Body Mapping Engine V2 — Run Script
====================================
Script para executar a delegação do Body Mapping V2.

Arquitetura: Agent Factory é plataforma de execução.
Agentes vivem em pta-mobile/agentes/.
Factory carrega sob demanda via AgentLoader.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.registry import get_registry
from src.protocols.schema import ProjectConfig
from src.notifications.windows import send_completion_notification, send_error_notification


def run_body_mapping_v2():
    """Executa a delegação do Body Mapping Engine V2."""
    
    print("=" * 60)
    print("Agent Factory — Body Mapping Engine V2")
    print("=" * 60)
    
    # 1. Registrar projeto
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
    
    # 2. Carregar agentes sob demanda
    print("\n2. Carregando agentes sob demanda...")
    refs = registry.list_agent_refs(project_id)
    agents = {}
    for agent_id in refs:
        agent = registry.load_agent(project_id, agent_id)
        agents[agent_id] = agent
        print(f"   - {agent_id} ({agent.role.value})")
    
    # Configurar subordinados
    agents["coordenador"].set_subordinates(agents)
    
    # 3. Executar Body Mapping V2
    print("\n3. Executando Body Mapping Engine V2...")
    print("   Fase 1: Core Mapping Engine (CV)")
    print("   Fase 2: Context Engine (CV)")
    print("   Fase 3: Integracao (Frontend)")
    print("   Fase 4: Validacao (QA)")
    
    result = agents["coordenador"].run({
        "task_id": "body-mapping-v2-main",
        "task_type": "body_mapping_v2",
        "payload": {},
    })
    
    # 4. Status final
    print("\n" + "=" * 60)
    print("Resultados:")
    print("=" * 60)
    
    success = True
    if result.output:
        for phase_result in result.output.get("results", []):
            phase = phase_result["phase"]
            status = phase_result["result"].get("status", "ok")
            print(f"   OK {phase}: {status}")
            if status == "error":
                success = False
    
    # 5. Enviar notificação Windows
    total_phases = len(result.output.get("results", [])) if result.output else 0
    completed_phases = total_phases if success else total_phases - 1
    
    if success:
        send_completion_notification(
            project_id,
            total_phases,
            completed_phases,
            0,
            0.0
        )
    else:
        send_error_notification(
            project_id,
            f"{completed_phases}/{total_phases} fases concluídas"
        )
    
    # 6. Context usage
    print("\n4. Context Usage:")
    for agent_id, agent in agents.items():
        usage = agent.get_context_usage()
        print(f"   - {agent_id}: {usage['used_kb']:.1f}KB / {usage['limit_kb']:.1f}KB ({usage['percentage']:.1f}%) [{usage['status']}]")
    
    print(f"\n   Dashboard: http://localhost:8080?project={project_id}")
    print("\nBody Mapping Engine V2 delegado com sucesso!")
    
    return project_id


if __name__ == "__main__":
    run_body_mapping_v2()
