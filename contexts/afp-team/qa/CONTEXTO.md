# QA — Agent Factory

## Proposito
Agente de qualidade do Agent Factory. Executa em seu proprio `AgentRuntime`,
consumindo tarefas da fila `task.run.qa` via RabbitMQ.

Valida codigo, executa testes e linters.

## Ambiente de Execucao

- Runtime autonomo com LLM proprio (`ollama:deepseek-r1:8b`)
- Recebe tarefas via Event Bus (RabbitMQ) ou fallback in-process

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

## Tarefa Imediata: Validar estado apos correcoes

**O que validar:**
1. Dashboard carrega sem erros no console (F12)
2. Projetos PTA e AFP-Team mostram contagem de agentes running independente
3. Navegacao entre abas AGENTS e Mission Control em cada projeto funciona
4. Mission Control Global e Local exibem missoes corretamente
5. Nao ha poluicao de estado entre projetos (agentes running de um NAO aparecem no outro)

**Como testar:**
1. Acesse `http://127.0.0.1:8080/#/projects` — verifique cards de projeto
2. Acesse PTA e AFP-Team — verifique se agentes running sao independentes
3. Verifique console para erros JS
4. Teste Mission Control Global e Local

## Working Directory
`C:\Users\rafae\agent-factory`

## Licoes Aprendidas (22/07/2026)

### Verificacao de isolamento entre projetos
Ao testar estado de agentes no dashboard, sempre verificar que projetos diferentes
nao contaminam as metricas uns dos outros. Agentes com mesmo ID (`coordenador`, `qa`,
`designer`) em projetos diferentes devem ter estados independentes.

### Escaneamento de console apos qualquer mudanca JS
Sempre verificar o console do navegador apos alteracoes no JavaScript. Erros comuns:
- `ReferenceError: Cannot access before initialization` (TDZ)
- `XXX is not defined` (variavel inexistente na template)
- TypeError em propriedades de `undefined`

## Validacao Git

Ao revisar o trabalho do dev, incluir estas verificacoes:

1. Verificar se `git status` mostra working tree limpo (sem mudancas nao commitadas)
2. Verificar se `git log --oneline -5` mostra mensagens de commit descritivas
3. Verificar se `git diff HEAD~1 --stat` mostra apenas arquivos relevantes no ultimo commit
4. Se houver mudancas nao commitadas, alertar o coordenador para que o dev commite antes de prosseguir

**Nunca aprovar uma missao se houver trabalho nao commitado em arquivos criticos** (`src/dashboard/index.html`, `src/dashboard/server.py`, `src/agents/`).
