import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: search_refs.py <file>")
        return
    filepath = sys.argv[1]
    replacements = {
        'project.name': 'project_name',
        'project.id': 'project_id',
        'agent.id': 'agent_id',
        'project.teams': None
    }
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines, start=1):
        for old, new in replacements.items():
            if old in line:
                found = True
                if new is None:
                    suggestion = "REMOVED: 'teams' array no longer exists"
                else:
                    suggestion = f"replace with '{new}' (may need to adjust code context)"
                print(f"Line {i}: found '{old}' -> {suggestion}")
                print(f"  Content: {line.strip()[:200]}")
    if not found:
        print("No references found.")

if __name__ == '__main__':
    main()
