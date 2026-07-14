from pathlib import Path

t = Path("src/dashboard/index.html").read_text(encoding="utf-8")
print(f"Size: {len(t)} bytes / {t.count(chr(10))} lines")
print(f"<!DOCTYPE: {t.count('<!DOCTYPE')}")
print(f"<style>: {t.count('<style')}")
print(f"<script>: {t.count('<script')}")
print(f"fetch(): {t.count('fetch(')}")
print(f"EventSource: {t.count('EventSource')}")
print(f"project-card: {t.count('project-card')}")
print(f"agent-card: {t.count('agent-card')}")
print(f"timeline: {t.count('timeline')}")
print(f"showProjects: {t.count('showProjects')}")
print(f"glass: {t.count('glass')}")
print(f"neon: {t.count('neon')}")
print(f"init: {t.count('init()')}")
print(f"Git diffs: {t.count('git diff')}")
print()
# Check git status
import subprocess
result = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True, cwd=".")
print("Git log:")
print(result.stdout)
