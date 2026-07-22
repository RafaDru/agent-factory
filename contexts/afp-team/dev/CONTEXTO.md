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

### Tarefa Imediata: Contextos atualizados — commit e push

**O que fazer:**
Todos os contextos foram atualizados com licoes desta sessaoo. Agora commitar e fazer push.

**Commits:**
1. `git add -A`
2. `git commit -m "fix: cross-project agent state isolation, Cache-Control, template bugs"`
3. `git push origin master`

**Verificar:**
- `git status` limpo
- Push bem-sucedido sem erros

**Working Directory:**
`C:\Users\rafae\agent-factory`

## Licoes Aprendidas (22/07/2026)

### 1. Escopo de chaves de estado global
Ao armazenar estado por agente em `state.agentsState`, sempre usar chave composta `projectId:agentId`.
Nunca usar `agentId` puro, pois IDs como `coordenador`, `qa`, `designer`, `negocios`, `arquiteto`
sao compartilhados entre projetos. Um projeto rodando 3 agentes inflava o contador dos demais.

Criar helper `agentKey(pId, aId) => \`${pId}:${aId}\`` e usar em todos os lookup/set.

### 2. Cache-Control em SPAs
Sempre adicionar `Cache-Control: no-cache, no-store, must-revalidate` no header HTTP
de respostas HTML. Sem isso, o navegador serve JS/CSS estale apos deploy, causando
bugs "ja corrigidos" que persistem para o usuario.

### 3. Temporal Dead Zone (TDZ) de `const`
Se uma template string referencia uma variavel `const` que e declarada depois dela,
o interpretador lanca `ReferenceError: Cannot access before initialization`.
Em arquivos grandes (+3000 linhas), manter declaracoes no topo ou verificar
a ordem de definicao antes de usar em templates.

### 4. Nomes de variaveis em templates
Ao usar `info.dotClass` e `info.label` em template, garantir que a variavel
realmente se chama `info` e nao `statusInfo`. Esse bug (referencia a `info` indefinido)
passou despercebido porque o template foi copiado de outro contexto.

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

