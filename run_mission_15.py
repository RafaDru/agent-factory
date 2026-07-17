"""
Missao #15: Validar ciclo missao -> reflexao -> arvore de contexto
Executa in-process para garantir que subordinates estejam wired.
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.registry import get_registry
from src.mcp.server import _wire_subordinates
from src.sdk.context_tree import ContextTree

project_id = "AFP-Team"
registry = get_registry()

# Carregar coordenador + subordinates
agent = registry.load_agent(project_id, "coordenador")
_wire_subordinates(registry, project_id, agent)

# Verificar arvore de contexto ANTES
tree = ContextTree(project_id, "coordenador")
tree.ensure_initialized()
stats_before = tree.stats()
print("Arvore de contexto ANTES:")
for dom, sz in stats_before.get("domains", {}).items():
    print("  %s: %d bytes" % (dom, sz))

# Executar missao
print("\nExecutando missao...")
task = {
    "task_id": "missao-validar-reflexao-15",
    "action": "plan_and_execute",
    "goal": "Adicionar docstring Google-style em todas as funcoes de src/eventbus/amqp.py",
    "context": "Manter o codigo existente. Apenas adicionar docstrings. Executar pytest apos."
}
start = time.time()
result = agent.run(task)
elapsed = time.time() - start

print("\n=== RESULTADO DA MISSAO ===")
print("Tempo: %.1fs" % elapsed)
print("Status:", result.status.value)
print("Summary:", result.summary)

output = result.output if hasattr(result, "output") else result
if isinstance(output, dict):
    print("Mission:", output.get("mission_id", "?"))
    print("Steps:", output.get("total_steps", "?"))
    print("Completed:", output.get("completed", "?"))
    print("Failed:", output.get("failed", "?"))
    for s in output.get("steps", []):
        print("  - %s (%s): %s / %s" % (
            s.get("step", "?"), s.get("agent_id", "?"),
            s.get("status", "?"), s.get("decision", "?"),
        ))

# Verificar arvore de contexto DEPOIS
print("\nArvore de contexto DEPOIS:")
stats_after = tree.stats()
for dom, sz in stats_after.get("domains", {}).items():
    before = stats_before.get("domains", {}).get(dom, 0)
    diff = sz - before
    mark = " (+%d bytes)" % diff if diff > 0 else ""
    print("  %s: %d bytes%s" % (dom, sz, mark))

# Verificar reflexao no CONTEXTO.md
ctx_path = agent.get_doc_path()
if Path(ctx_path).exists():
    content = Path(ctx_path).read_text(encoding="utf-8")
    if "## Retrospectiva de Missoes" in content:
        print("\nCONTEXTO.md: Reflexao pos-missao PRESENTE")
    else:
        print("\nCONTEXTO.md: Reflexao AUSENTE")

print("\nDone!")
