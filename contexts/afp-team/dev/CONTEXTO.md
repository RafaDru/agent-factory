# Dev — Agent Factory Platform (AFP)

## Proposito
Agente de desenvolvimento da plataforma Agent Factory. Executa em seu proprio
`AgentRuntime`, consumindo tarefas da fila `task.run.dev` via RabbitMQ.

Opera arquivos reais no sistema de arquivos: leitura, escrita, edicao,
execucao de scripts, git e descoberta de diretorios.

## Ambiente de Execucao

- Runtime autonomo com LLM proprio (`ollama:deepseek-r1:8b`)
- Recebe tarefas via Event Bus (RabbitMQ) ou fallback in-process
- Tem acesso completo ao sistema de arquivos e git

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
| get_capabilities | Retorna acoes disponiveis |

## Estado Atual do Projeto

O Console AFP esta em `src/dashboard/index.html` (HTML+CSS+JS inline, unico arquivo).
O servidor esta em `src/dashboard/server.py`.

### Funcionalidades Implementadas
- Mission Control com cards de missao, cadeia de delegacao, Log Details
- Configuracao com 3 abas (Projetos, Agentes, LLM Providers)
- URL routing via hash
- LLM Modal com benchmarks

### Tarefa Imediata: Remover botao "Detalhes" do Mission Control

**O que fazer:**
No `renderMissionCard()` em `src/dashboard/index.html`, remover o botao "📋 Detalhes".

**Instrucoes:**
1. Leia `src/dashboard/index.html`
2. Encontre a funcao `renderMissionCard()` — procure pelo HTML que contem `live-detail-btn`
3. Remova a linha do botao "📋 Detalhes" (a que tem `onclick="document.getElementById('${detailId}')..."`)
4. Nao remova o "📋 Log Details" — apenas o "📋 Detalhes"
5. Nao remova a div `live-timeline` ou o `detailId` — eles podem ser mantidos ou removidos
6. A variavel `detailId` (`const detailId = 'detail-' + ...`) pode ser removida se nao for mais usada

## Working Directory
`C:\Users\rafae\agent-factory`

## Git Workflow — Protecao de Trabalho

**Contexto:** Ja perdemos ~70KB de codigo do dashboard por um `git checkout` sem commit. Isso nao pode se repetir.

### Regras Obrigatorias:

1. **SEMPRE commitar antes de qualquer operacao destrutiva** (`git checkout`, `git reset`, `git rebase`)
2. **NUNCA usar `git checkout HEAD -- <caminho>`** — isso descarta mudancas nao commitadas
3. **Commits frequentes**: ao concluir uma alteracao funcional, commite imediatamente
4. **Mensagens de commit padrao:**
   - `feat: descricao` — nova funcionalidade
   - `fix: descricao` — correcao de bug
   - `refactor: descricao` — refatoracao sem mudanca funcional
   - `docs: descricao` — documentacao
   - `chore: descricao` — tarefa de manutencao
5. **SEMPRE revisar com `git diff --stat`** antes de commitar para garantir que apenas os arquivos desejados serao incluidos
6. **Nao incluir arquivos grandes ou binarios** no commit (verificar `.gitignore`)
7. **Nao editar o mesmo arquivo que outro agente** sem coordenacao previa

### Fluxo Seguro:
```bash
git status                    # 1. Verificar estado
git diff                      # 2. Revisar mudancas
git add src/caminho/arquivo   # 3. Adicionar arquivos especificos
git commit -m "tipo: descricao" # 4. Commitar
```

### Recuperacao de Trabalho Perdido:
Se perceber que perdeu trabalho, ANTES de fazer qualquer outra coisa:
```bash
git reflog       # Ver historico de operacoes
git stash list   # Ver stashes salvos
```
Sempre notificar o coordenador imediatamente se houver perda de codigo.

