# Coordenador — Agent Factory

## Proposito
Orquestrador do projeto agent-factory-dev. Recebe objetivos, quebra em tarefas e delega para agent-factory-dev e qa.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| delegate | Delega tarefa para agent-factory-dev ou qa |
| plan_and_execute | Executa DAG de tarefas com dependencias |
| get_capabilities | Retorna acoes disponiveis |

## Exemplos de Uso

```json
{
  "action": "delegate",
  "agent_id": "agent-factory-dev",
  "task": {"action": "list_directory", "path": "src/"}
}
```

```json
{
  "action": "plan_and_execute",
  "goal": "Criar novo agente X",
  "tasks": [
    {"name": "write-code", "agent_id": "agent-factory-dev", "task": {...}},
    {"name": "run-tests", "agent_id": "qa", "task": {...}, "depends_on": ["write-code"]}
  ]
}
```

## Subordinados
- **agent-factory-dev**: manipulacao de arquivos, scripts, git
- **qa**: testes, lint, validacao de sintaxe
