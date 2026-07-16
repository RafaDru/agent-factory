import subprocess
import sys
import json

def run_gh(args):
    result = subprocess.run(['gh'] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'Erro ao executar gh: {result.stderr}', file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()

if len(sys.argv) < 3:
    print('Uso: move_issue.py <issue_number> <status> [comment]')
    sys.exit(1)

issue_number = sys.argv[1]
new_status = sys.argv[2]
comment = sys.argv[3] if len(sys.argv) > 3 else None

if issue_number == 'None':
    print('Nenhuma issue para mover.')
    sys.exit(0)

# Obter item-id
item_id = run_gh(['project', 'item-list', '4', '--owner', '@me', '--format', 'json', '--jq', f'.[] | select(.content.number=={issue_number}) | .id'])
if not item_id:
    print(f'Issue #{issue_number} não encontrada no projeto.')
    sys.exit(1)

# Mover para o status desejado
run_gh(['project', 'item-edit', '--project', '4', '--id', item_id, '--status', new_status])
print(f'Issue #{issue_number} movida para {new_status}.')

# Adicionar comentário se fornecido
if comment:
    run_gh(['issue', 'comment', issue_number, '--body', comment])
    print(f'Comentário adicionado à issue #{issue_number}.')
