import sys
sys.path.insert(0, ".")
from src.llm import get_provider

p = get_provider("smart")

prompts = [
    ("coder", "Gere uma funcao Python que calcula o PR (Performance Ratio) de um sistema solar"),
    ("fast", "Responda apenas sim ou nao: 2+2=4?"),
]

for task_type, msg in prompts:
    print(f"\n{'='*60}")
    print(f"Task: {task_type}")
    print(f"Msg: {msg}")
    print('='*60)
    try:
        resp = p.chat(
            messages=[{"role": "user", "content": msg}],
            temperature=0.3,
            max_tokens=500,
        )
        print(f"Provider: {resp.model}")
        print(f"Tokens: {resp.usage}")
        print(f"Resp: {resp.content[:300]}...")
    except Exception as e:
        print(f"Error: {e}")
