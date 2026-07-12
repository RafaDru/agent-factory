import sys
sys.path.insert(0, ".")
from src.llm import get_provider, SmartRouterProvider

# Teste basico
p = get_provider("smart")
print(f"SmartRouter available={p.is_available()}")
print(f"SmartRouter type={type(p).__name__}")

p2 = get_provider("auto")
print(f"Auto: {type(p2).__name__}")
print(f"Auto is SmartRouter: {type(p2).__name__ == 'SmartRouterProvider'}")

# Teste: detect task type
router = SmartRouterProvider()
tests = [
    ("Implemente uma funcao em Python que calcula fibonacci", "coder"),
    ("Analise os dados de geracao solar e compare com o mes passado", "analysis"),
    ("Explique por que o PR caiu nos ultimos 7 dias", "reasoner"),
    ("Classifique este alerta como baixo, medio ou alto", "fast"),
    ("Crie um plano de implementacao para o modulo de logging", "planner"),
    ("Revise este codigo e aponte possiveis bugs", "review"),
]

print("\n--- Task Type Detection ---")
for msg, expected in tests:
    detected = router._detect_task_type([{"role": "user", "content": msg}])
    ok = "OK" if detected == expected else f"GOT {detected}"
    print(f"  [{ok:20s}] expected={expected:10s} msg={msg[:50]}")

# Teste: ver ranking de cada task type
print("\n--- Rankings ---")
for ttype, rank in SmartRouterProvider.RANKINGS.items():
    print(f"  {ttype:10s}: {' → '.join(rank)}")
