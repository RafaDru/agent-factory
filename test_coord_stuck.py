import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
if not registry.project_exists("AFP-Team"):
    registry.register(ProjectConfig(project_id="AFP-Team", name="AFP-Team"))

coord = registry.load_agent("AFP-Team", "coordenador")
print(f"Coordinator LLM: {type(coord._llm).__name__ if coord._llm else 'NONE'}")
print(f"LLM available: {coord._llm.is_available() if coord._llm else False}")
print("Testing chat...")
try:
    r = coord._llm.chat([{"role": "user", "content": "Reply OK"}], max_tokens=10)
    print(f"Response: {r.content.strip() if r else 'EMPTY'}")
except Exception as e:
    import traceback
    traceback.print_exc()
