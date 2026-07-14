import re
from pathlib import Path

base = Path(".agent-factory/missions/missao-redesenhar-completamente-dashboard-agent-factory-platform/output/tasks")

# Collect all HTML blocks from all Dev artifacts
all_blocks = []

for task_name in sorted(base.iterdir()):
    if not task_name.is_dir() or not task_name.name.startswith("implementar"):
        continue
    artifact = task_name / "dev" / "artifacts" / "llm_raw_response.md"
    if not artifact.exists():
        continue
    
    text = artifact.read_text(encoding="utf-8")
    
    # Find all code blocks with HTML content
    # Match: ```html ... ``` or ``` ... ``` containing <!DOCTYPE
    pattern = r'```(?:html)?\s*\n(.*?)```'
    blocks = re.findall(pattern, text, re.DOTALL)
    
    for i, block in enumerate(blocks):
        if '<!DOCTYPE' in block or '<html' in block:
            size = len(block)
            all_blocks.append((task_name.name, i, size, block))

# Sort by size (most comprehensive first)
all_blocks.sort(key=lambda x: -x[2])

print("HTML blocks found (sorted by size):")
for name, idx, size, _ in all_blocks:
    print(f"  {name}/block{idx}: {size:6d} chars")

# Combine the largest CSS block with the largest HTML structure
if all_blocks:
    # Use the largest as base
    best = all_blocks[0][3]
    
    # Also extract CSS/JS from other blocks if they have it
    for _, _, _, block in all_blocks[1:]:
        # Extract <style> blocks from this one
        styles = re.findall(r'<style>(.*?)</style>', block, re.DOTALL)
        for s in styles:
            if s.strip() and s.strip() not in best:
                best = best.replace('</style>', '\n/* merged */\n' + s + '\n</style>')
        scripts = re.findall(r'<script>(.*?)</script>', block, re.DOTALL)
        for s in scripts:
            if s.strip() and s.strip() not in best:
                best = best.replace('</script>', '\n// merged\n' + s + '\n</script>')
    
    out = Path("src/dashboard/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(best, encoding="utf-8")
    print(f"\n  Merged {len(all_blocks)} blocks -> {out} ({len(best)} chars)")
