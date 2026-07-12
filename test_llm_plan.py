"""
Direct test of coordinator LLM plan generation
"""
import sys, json
from pathlib import Path
sys.path.insert(0, '.')

from src.agents.coordinator import AgentFactoryCoordinator
from src.llm import get_provider

# Use Ollama directly (skip auto / multi-model to avoid classification overhead)
provider = get_provider("ollama", model="qwen2.5-coder:7b")
print(f'Provider: {type(provider).__name__} model={provider.model}')

# Create coordinator
from src.protocols.events import EventNotifier
notifier = EventNotifier("test-coord", output_dir=".agent-factory/events")

coord = AgentFactoryCoordinator(
    project_id="agent-factory-dev",
    notifier=notifier,
    llm_provider=provider,
)
print(f'Coordinator LLM: {type(coord.llm_provider).__name__}')

# Generate plan
goal = 'Listar arquivos Python no diretorio src/'
print(f'\nGerando plano para: {goal}')
try:
    plan = coord._plan_with_llm(goal, context='Usar list_directory com pattern *.py')
    print(f'\nPlano gerado: {len(plan)} tarefas')
    for t in plan:
        print(f'  - {t["name"]} -> {t["agent_id"]} ({t["task"]["action"]})')
    print(f'\nJSON do plano:')
    print(json.dumps(plan, indent=2))
except Exception as e:
    print(f'ERRO: {e}')
    import traceback
    traceback.print_exc()
