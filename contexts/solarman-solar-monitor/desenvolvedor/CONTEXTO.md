# Desenvolvedor — SOLARMAN Solar Monitor

## Proposito
Implementar todas as evolucoes tecnicas necessarias para o monitor solar. Codigo organizado, versionado, testado e otimizado.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| implement | Implementa nova feature/correcao no codigo |
| refactor | Refatora codigo existente para melhor performance/manutencao |
| test | Cria ou executa testes |
| deploy | Prepara/configura deploy |
| read_file | Le conteudo de um arquivo |
| write_file | Escreve conteudo em arquivo |
| run_script | Executa script Python |
| run_git | Executa comandos git |

## Stack
- Python 3 + requests + psycopg2-binary
- PostgreSQL (GCP Cloud SQL)
- ntfy.sh (notificacoes)
- GCP Cloud Run + Cloud Scheduler

## Diretorio de trabalho
C:\Users\rafae\agent-factory

## Notas
- O projeto solar esta em C:\Users\rafae\agent-factory (nao no Workspace)
- Usar SmartRouter para LLM: get_provider("auto") que faz fallback groq > deepseek > mimo
- Schema SQL: src/supabase/migrations/schema.sql
- Monitor: src/monitor.py
- Tests: tests/

## Exemplos
```json
{"action": "implement", "code": "def nova_funcao():\n    pass"}
{"action": "refactor", "file_path": "monitor.py", "description": "Extrair logica de notificacao para modulo separado"}
{"action": "test", "path": "tests/", "args": ["-q"]}
```
