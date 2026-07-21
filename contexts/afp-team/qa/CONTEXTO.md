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

## Tarefa Imediata: Validar remocao do botao "Detalhes" no Mission Control

**O que validar:**
1. O botao "📋 Detalhes" foi removido do HTML renderizado pelo `renderMissionCard()`
2. O botao "📋 Log Details" continua presente e funcional
3. Nao ha erros no console do navegador apos a remocao
4. A variavel `detailId` pode ter sido removida — verificar se nao causa erro de referencia

**Como testar:**
1. Apos a modificacao do dev, reinicie o servidor (`python _run_dashboard.py`)
2. Acesse `http://127.0.0.1:8080/#/project/AFP-Team/mission-control`
3. Verifique visualmente se o botao "📋 Detalhes" nao aparece nos cards de missao
4. Clique em "📋 Log Details" para garantir que a tabela de logs abre corretamente
5. Verifique o console do navegador (F12) para erros JavaScript

## Working Directory
`C:\Users\rafae\agent-factory`

## Validacao Git

Ao revisar o trabalho do dev, incluir estas verificacoes:

1. Verificar se `git status` mostra working tree limpo (sem mudancas nao commitadas)
2. Verificar se `git log --oneline -5` mostra mensagens de commit descritivas
3. Verificar se `git diff HEAD~1 --stat` mostra apenas arquivos relevantes no ultimo commit
4. Se houver mudancas nao commitadas, alertar o coordenador para que o dev commite antes de prosseguir

**Nunca aprovar uma missao se houver trabalho nao commitado em arquivos criticos** (`src/dashboard/index.html`, `src/dashboard/server.py`, `src/agents/`).
