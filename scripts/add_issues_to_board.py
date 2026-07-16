**Plano de Implementação**

1. **Criar diretório `scripts/`** (se não existir) na raiz do projeto.
2. **Criar arquivo `scripts/add_issues_to_board.py`** com:
   - Shebang `#!/usr/bin/env python3` para facilitar execução.
   - Leitura do argumento JSON via `sys.argv[1]`.
   - Parsing do JSON para lista de issues.
   - Iteração sobre as issues, extraindo o campo `number`.
   - Para cada número, montar e executar o comando `gh project item-add 4 --owner @me --url https://github.com/RafaDru/agent-factory/issues/<number>`.
   - Tratamento de erros: capturar exceções de JSON, subprocess, e argumentos ausentes.
   - Exibir saída de cada comando e resumo final.
3. **Teste manual** (opcional): executar com o JSON de exemplo fornecido para validar.

**Arquivos a serem criados/modificados**
- `scripts/add_issues_to_board.py` (novo)

**Código**

```python
#!/usr/bin/env python3
"""
Script para adicionar issues abertas ao board #4 do GitHub Project.

Uso:
    python scripts/add_issues_to_board.py '<json_string>'

O JSON deve ser a saída do comando:
    gh issue list --repo RafaDru/agent-factory --state open --json title,number,labels
"""

import sys
import json
import subprocess
from typing import List, Dict

def add_issues_to_board(issues_json: str) -> None:
    """Adiciona cada issue ao board #4 via GitHub CLI."""
    try:
        issues: List[Dict] = json.loads(issues_json)
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
        sys.exit(1)

    if not isinstance(issues, list):
        print("JSON não é uma lista de issues.")
        sys.exit(1)

    success_count = 0
    error_count = 0

    for issue in issues:
        number = issue.get("number")
        if not number:
            print(f"Issue sem número: {issue}")
            error_count += 1
            continue

        url = f"https://github.com/RafaDru/agent-factory/issues/{number}"
        cmd = [
            "gh", "project", "item-add", "4",
            "--owner", "@me",
            "--url", url
        ]

        print(f"Adicionando issue #{number} ao board...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print(f"  ✓ Sucesso: {result.stdout.strip()}")
                success_count += 1
            else:
                print(f"  ✗ Erro (código {result.returncode}): {result.stderr.strip()}")
                error_count += 1
        except FileNotFoundError:
            print("  ✗ Comando 'gh' não encontrado. Verifique se GitHub CLI está instalado.")
            error_count += 1
        except Exception as e:
            print(f"  ✗ Exceção: {e}")
            error_count += 1

    print(f"\nResumo: {success_count} issues adicionadas, {error_count} falhas.")

def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/add_issues_to_board.py '<json_string>'")
        sys.exit(1)

    issues_json = sys.argv[1]
    add_issues_to_board(issues_json)

if __name__ == "__main__":
    main()
```

**Observações**
- O script assume que o GitHub CLI (`gh`) está autenticado e disponível no PATH.
- O board #4 deve existir e ser acessível ao usuário autenticado.
- Se alguma issue já estiver no board, o comando `gh project item-add` pode falhar com erro de duplicata; isso é tratado como erro, mas pode ser ajustado conforme necessidade.