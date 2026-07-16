# Coordenador — Agent Factory

## Proposito
Orquestrador do projeto afp. Recebe objetivos em linguagem natural, gera planos via LLM (Groq/Ollama) e delega para dev e qa.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| delegate | Delega tarefa para dev ou qa |
| plan_and_execute | Gera plano via LLM ou recebe tasks manuais e executa DAG com dependencias |
| get_capabilities | Retorna acoes disponiveis |

## Modo 1: Geracao Automatica (LLM)

Forneca apenas o objetivo. O coordenador chama o LLM para gerar o plano.

```json
{
  "action": "plan_and_execute",
  "goal": "Listar arquivos Python em src/ e rodar pytest",
  "context": "Usar list_directory com pattern *.py e run_tests com args -q"
}
```

O LLM analisa o objetivo e retorna um JSON com as tarefas e dependencias.

## Modo 2: Tasks Manuais (sem LLM)

Forneca as tasks explicitamente para execucao direta.

```json
{
  "action": "plan_and_execute",
  "goal": "Validar ambiente Agent Factory",
  "tasks": [
    {"name": "list-src", "agent_id": "dev", "task": {"action": "list_directory", "path": "src/", "pattern": "*.py"}, "depends_on": []},
    {"name": "run-tests", "agent_id": "qa", "task": {"action": "run_tests", "path": "tests/", "args": ["-q"]}, "depends_on": ["list-src"]}
  ]
}
```

## Delegacao Direta

```json
{
  "action": "delegate",
  "agent_id": "dev",
  "task": {"action": "list_directory", "path": "src/"}
}
```

## Subordinados
- **dev**: manipulacao de arquivos, scripts, git
- **qa**: testes, lint, validacao de sintaxe

## Provedor LLM
- Usa `get_provider("auto")`: tenta Groq (cloud) -> Ollama (local) -> Mock
- Para usar local: `ollama` rodando em http://localhost:11434

## Licoes Aprendidas

### Orquestracao e Know-How

- **Event delegation**: Usar `document.addEventListener('click')` com `closest()` para elementos renderizados dinamicamente. Manter o listener no escopo global, nunca aninhado dentro de outra função.
- **Timestamps**: No backend, usar `datetime.now(timezone.utc)` para gerar timestamps com timezone. No frontend, se receber string naive, anexar 'Z' para forçar interpretação UTC e evitar que o JS interprete como hora local.
- **Interaction Flow**: Garantir que a função `switchView()` carregue eventos históricos de `/api/events` e popule `agentState.events` para exibir o fluxo de interação completo.

