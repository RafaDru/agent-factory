import os, sys
sys.path.insert(0, '.')
from src.llm import get_provider

# Check env var
key = os.getenv("GEMINI_API_KEY")
print(f"GEMINI_API_KEY: {'SET' if key else 'NOT SET'}")
if key:
    print(f"Key: {key[:15]}...{key[-4:]}")

# Check provider
p = get_provider("gemini")
print(f"Available: {p.is_available()}")
print(f"Model: {getattr(p, 'model', '?')}")

# Test API call
try:
    resp = p.chat(
        messages=[{"role":"user","content":"Reply with just the number 42"}],
        temperature=0.1,
        max_tokens=20,
    )
    print(f"SUCCESS: {resp.content.strip()}")
    usage = resp.usage or {}
    print(f"Tokens: {usage.get('total_tokens', '?')}")
    print(f"Model used: {getattr(resp, 'model', '?')}")
except Exception as e:
    print(f"ERROR: {e}")
