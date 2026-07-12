import sys
sys.path.insert(0, ".")

from src.llm import get_provider

print("Testando provedores cloud gratuitos...\n")

for name in ["deepseek", "openrouter"]:
    try:
        p = get_provider(name)
        avail = p.is_available()
        print(f"[{name}] available={avail} type={type(p).__name__}")
        if avail:
            resp = p.chat(
                messages=[{"role": "user", "content": "Responda apenas: OK"}],
                max_tokens=50,
            )
            print(f"  model={resp.model} tokens={resp.usage} response={resp.content[:100]}")
    except Exception as e:
        print(f"[{name}] ERROR: {e}")

print("\nTestando auto-detect:")
auto = get_provider("auto")
print(f"  Auto escolheu: {type(auto).__name__}")
print(f"  Disponivel: {auto.is_available()}")
