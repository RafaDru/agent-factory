# Dev — Agent Factory Platform (AFP)

## Proposito
Agente de desenvolvimento da plataforma Agent Factory. Opera arquivos reais no sistema de arquivos: leitura, escrita, edicao, execucao de scripts, git e descoberta de diretorios.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| read_file | Le conteudo de um arquivo |
| write_file | Escreve conteudo em arquivo (cria diretorios automaticamente) |
| edit_file | Substitui texto em arquivo existente |
| run_script | Executa script Python via subprocess |
| run_tests | Executa pytest em diretorio especifico |
| run_git | Executa comandos git (add, commit, push, diff, etc.) |
| list_directory | Lista arquivos em diretorio com filtro opcional (pattern) |
| generate_code | Gera codigo via LLM (React, Python, etc) |
| implement_feature | Usa LLM para planejar e implementar uma feature |
| refactor_code | Usa LLM para analisar e refatorar codigo existente |
| get_capabilities | Retorna acoes disponiveis com parametros |

## Exemplos

```json
{"action": "read_file", "file_path": "src/agents/base.py"}
{"action": "write_file", "file_path": "src/agents/novo_agente.py", "content": "..."}
{"action": "run_tests", "path": "tests/", "args": ["-x", "--tb=short"]}
{"action": "run_git", "args": ["add", "."], "workdir": "."}
{"action": "generate_code", "spec": "Criar componente React ProjectCard com EUI", "output_path": "dashboard-react/src/components/ProjectCard.jsx"}
{"action": "refactor_code", "file_path": "src/agents/base.py", "instructions": "Adicionar type hints"}
```

## Working Directory
`C:\Users\rafae\agent-factory`
