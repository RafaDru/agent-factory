# QA — Agent Factory

## Proposito
Agente de qualidade do Agent Factory. Valida codigo, executa testes e linters.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| run_tests | Executa pytest com saida detalhada |
| lint | Executa ruff check (opcional: --fix) |
| type_check | Executa pyright para tipos |
| validate_python_syntax | Valida sintaxe Python de um arquivo |
| review_code | Usa LLM para revisar codigo (boas praticas, seguranca, qualidade) |
| suggest_fixes | Usa LLM para analisar falhas e sugerir correcoes |
| analyze_project | Usa LLM para analisar saude geral do projeto |
| get_capabilities | Retorna acoes disponiveis |

| test_event_pipeline | Executa pytest tests/test_event_pipeline.py -v e valida o pipeline de eventos |

## Exemplos

```json
{"action": "run_tests", "path": "tests/test_all.py", "args": ["-q"]}
{"action": "lint", "path": "src/", "fix": true}
{"action": "validate_python_syntax", "file_path": "src/agents/base.py"}
{"action": "review_code", "file_path": "src/agents/factory_dev.py"}
{"action": "suggest_fixes", "error": "pytest failed with AssertionError", "file_path": "tests/test_all.py"}
{"action": "analyze_project", "path": "src/"}

{"action": "run_tests", "path": "tests/test_event_pipeline.py", "args": ["-v"]}
```

## Notas
- pyright precisa estar instalado globalmente (npm install -g pyright)
- pytest e ruff sao dependencias do projeto


## Testes de Pipeline de Eventos

O QA deve validar que:
- Eventos sao emitidos durante execucao de missoes
- Eventos persistem em .agent-events/<project>/events.jsonl
- REST /api/events retorna eventos apos missao
- SSE entrega eventos em tempo real
- Painel de logs no frontend exibe eventos corretamente
