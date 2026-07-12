import sys
sys.path.insert(0, ".")
from src.llm import get_provider

# Test MIMO with corrected endpoint
print("=== Testando MIMO (corrigido) ===")
p = get_provider("mimo")
print(f"  URL: {p.base_url}")
print(f"  Model: {p.model}")
print(f"  Available: {p.is_available()}")

# Test Groq (lib installed now)
print("\n=== Testando GroQ (recem instalado) ===")
p = get_provider("groq")
print(f"  Model: {p.model}")
print(f"  Available: {p.is_available()}")

# Test Cerebras corrected model
print("\n=== Testando Cerebras (modelo corrigido) ===")
p = get_provider("cerebras")
print(f"  Model: {p.model}")
print(f"  Available: {p.is_available()}")

# Test smart router chain
print("\n=== SmartRouter: chain completa ===")
from src.llm import SmartRouterProvider
for name in SmartRouterProvider.RANKINGS["default"]:
    p = SmartRouterProvider._make_provider(name)
    if p:
        print(f"  {name:15s} available={p.is_available():5} url={getattr(p, 'base_url', getattr(p, '_client', 'N/A'))}")
    else:
        print(f"  {name:15s} FAILED TO CREATE")

print("\n=== Teste de chat com SmartRouter ===")
p = get_provider("smart")
try:
    resp = p.chat(
        messages=[{"role": "user", "content": "Gere uma funcao Python que calcula o PR de um sistema solar"}],
        max_tokens=200,
    )
    print(f"Sucesso! Provider: {resp.model}")
    print(f"  Tokens: {resp.usage}")
    print(f"  Conteudo: {resp.content[:200]}...")
except Exception as e:
    print(f"Erro: {e}")
