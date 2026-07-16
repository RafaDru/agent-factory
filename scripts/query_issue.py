import subprocess
import json
import sys

def run_gh(args):
    result = subprocess.run(['gh'] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'Erro ao executar gh: {result.stderr}', file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()

# Listar issues do projeto #4 com label priority-high
issues_json = run_gh(['issue', 'list', '--project', '4', '--label', 'priority-high', '--json', 'number,title,state'])
issues = json.loads(issues_json)

# Prioridade: #2, #3, #5 (se estiverem com estado 'open' e no board como Todo?)
# O estado 'open' indica que a issue está aberta, mas precisamos verificar o status no board.
# Vamos buscar o status do item no projeto.
# Para cada issue, obter o item-id e status.
priority_order = [2, 3, 5]
selected = None
for num in priority_order:
    # Verificar se a issue existe na lista e está aberta
    issue = next((i for i in issues if i['number'] == num), None)
    if issue and issue['state'] == 'OPEN':
        # Obter status no projeto
        item_id = run_gh(['project', 'item-list', '4', '--owner', '@me', '--format', 'json', '--jq', f'.[] | select(.content.number=={num}) | .id'])
        if item_id:
            status = run_gh(['project', 'item-view', '4', item_id, '--jq', '.status'])
            if status == 'Todo':
                selected = {'number': num, 'title': issue['title']}
                break

if not selected:
    # Se nenhuma das prioritárias estiver Todo, pegar a mais antiga com status Todo
    for issue in issues:
        if issue['state'] == 'OPEN':
            item_id = run_gh(['project', 'item-list', '4', '--owner', '@me', '--format', 'json', '--jq', f'.[] | select(.content.number=={issue["number"]}) | .id'])
            if item_id:
                status = run_gh(['project', 'item-view', '4', item_id, '--jq', '.status'])
                if status == 'Todo':
                    selected = {'number': issue['number'], 'title': issue['title']}
                    break

if selected:
    print(json.dumps(selected))
else:
    print(json.dumps({'number': None, 'title': None}))
