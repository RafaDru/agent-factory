import re
from pathlib import Path

f = Path(".agent-factory/missions/missao-redesenhar-completamente-dashboard-agent-factory-platform/output/tasks/implementar-estrutura-html-base/dev/artifacts/llm_raw_response.md")
text = f.read_text(encoding="utf-8")

# Check if there are backticks at all
count = text.count('```')
print(f"Backtick sequences (```): {count}")

# Find all code blocks more carefully
blocks = re.findall(r'```.*?\n(.*?)```', text, re.DOTALL)
print(f"Code blocks found: {len(blocks)}")
for i, b in enumerate(blocks):
    print(f"  Block {i}: {len(b)} chars  starts: {b.strip()[:50]}")
