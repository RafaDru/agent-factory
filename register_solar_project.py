#!/usr/bin/env python3
"""Registra o projeto solarman-solar-monitor no Agent Factory."""
import sys
sys.path.insert(0, r"C:\Users\rafae\agent-factory")

from src.registry import get_registry
from src.protocols.schema import ProjectConfig
from src.loader import AgentReference

BASE = r"C:\Users\rafae\agent-factory"
SOLAR = r"C:\Users\rafae\Workspace\solarman-solar-monitor"
CONTEXTS = rf"{BASE}\contexts\solarman-solar-monitor"

registry = get_registry()

# 1. Registrar projeto
config = ProjectConfig(
    project_id="solarman-solar-monitor",
    name="SOLARMAN Solar Monitor",
    description="Monitoramento de geracao solar residencial com 2 microinversores Deye e 7 paineis. "
                "Coleta dados da API SOLARMAN e armazena em PostgreSQL.",
)
registry.register(config)
print(f"Projeto registrado: {config.project_id}")

# 2. Adicionar referencias dos agentes
agents = [
    AgentReference(
        agent_id="coordenador",
        module_path=rf"{SOLAR}\agentes",
        class_name="SolarCoordinator",
        context_file=rf"{CONTEXTS}\coordenador\CONTEXTO.md",
        context_limit_kb=15.0,
    ),
    AgentReference(
        agent_id="negocios",
        module_path=rf"{SOLAR}\agentes",
        class_name="NegociosAgent",
        context_file=rf"{CONTEXTS}\negocios\CONTEXTO.md",
        context_limit_kb=15.0,
    ),
    AgentReference(
        agent_id="desenvolvedor",
        module_path=rf"{SOLAR}\agentes",
        class_name="DesenvolvedorAgent",
        context_file=rf"{CONTEXTS}\desenvolvedor\CONTEXTO.md",
        context_limit_kb=15.0,
    ),
    AgentReference(
        agent_id="design",
        module_path=rf"{SOLAR}\agentes",
        class_name="DesignAgent",
        context_file=rf"{CONTEXTS}\design\CONTEXTO.md",
        context_limit_kb=15.0,
    ),
]

for ref in agents:
    registry.add_agent_ref("solarman-solar-monitor", ref)
    print(f"  Agente registrado: {ref.agent_id} ({ref.class_name})")

# 3. Verificar
print("\n--- Verificacao ---")
for ref_id, ref in registry.list_agent_refs("solarman-solar-monitor").items():
    print(f"  {ref_id}: {ref.class_name} -> {ref.module_path}")

print("\nProjetos registrados:", [p.project_id for p in registry.list_projects()])
print("OK!")
