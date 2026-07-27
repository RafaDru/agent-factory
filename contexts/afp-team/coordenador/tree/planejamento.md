# Planejamento — coordenador — AFP-Team

## Estrategias

### missao-missao-010-refresh-tasks-grupos-colapsaveis-timer-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento (DAG):** O DAG atribuiu ações de implementação (`implement_feature`) ao agente `designer`, cujas capacida


### missao-missao-010-refresh-tasks-grupos-colapsaveis-timer
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento (DAG):** O DAG atribuiu ações de implementação (`implement_feature`) ao agente `designer`, cujas capacida


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento (DAG):** A missão foi estruturada como três tarefas independentes (listar-agents, listar-dashboard, valid


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento (DAG):** A missão foi estruturada como três tarefas independentes (listar-agents, listar-dashboard, valid


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: A missão falhou em suas etapas de desenvolvimento, com ambos os agentes `dev` retornando `failure` sem detalhes, sugerin


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: A missão falhou em suas etapas de desenvolvimento, com ambos os agentes `dev` retornando `failure` sem detalhes, sugerin


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: A missão revelou fragilidades no planejamento e na execução. O DAG previa que as tarefas de listagem (dev) fossem pré-re


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: A missão revelou fragilidades no planejamento e na execução. O DAG previa que as tarefas de listagem (dev) fossem pré-re


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento:** O DAG previa duas tarefas de listagem executadas por agentes `dev` e uma validação por `qa` dependente


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento:** O DAG previa duas tarefas de listagem executadas por agentes `dev` e uma validação por `qa` dependente


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: A missão foi estruturada com um DAG simples: dois agentes dev em paralelo (listar-agents e listar-dashboard) e, na sequê


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: A missão foi estruturada com um DAG simples: dois agentes dev em paralelo (listar-agents e listar-dashboard) e, na sequê


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento (DAG):** O DAG estava correto ao encadear as tarefas de listagem (dev) antes da validação (qa). A falha n


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento (DAG):** O DAG estava correto ao encadear as tarefas de listagem (dev) antes da validação (qa). A falha n


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento e delegação:** O DAG previa duas tarefas de desenvolvimento (`listar-agents` e `listar-dashboard`) seguid


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: **Planejamento e delegação:** O DAG previa duas tarefas de desenvolvimento (`listar-agents` e `listar-dashboard`) seguid


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc-planejamento
- **Acao**: reflect_on_mission
- **Resumo**: A missão foi estruturada com um DAG simples e coerente: listar diretórios (agentes dev) e validar sintaxe (agente qa). A


### missao-missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Acao**: reflect_on_mission
- **Resumo**: A missão foi estruturada com um DAG simples e coerente: listar diretórios (agentes dev) e validar sintaxe (agente qa). A


### Estrutura do DAG
- Tasks de leitura/levantamento primeiro (sem dependencias)
- Tasks de implementacao dependem de leitura
- Tasks de validacao/teste dependem de implementacao
- Tasks de deploy/commit sao as ultimas

### Politica de Git e Protecao de Trabalho

**Regras Obrigatorias:**
1. NUNCA usar `git checkout HEAD -- <arquivo>` em arquivos modificados
2. SEMPRE `git add` + `git commit` antes de reset/checkout
3. Antes de editar, verificar `git status` para mudancas nao salvas
4. Commits frequentes e atomicos: cada alteracao funcional = um commit
5. Stash antes de operacoes destrutivas: `git stash push -m "desc"` e `git stash pop`
6. Nao editar o mesmo arquivo em paralelo sem coordenacao

**Fluxo Git para o Dev:**
1. `git status` → `git diff` → `git add` → `git commit -m "tipo: desc"` → `git push`

**Se perder trabalho:**
1. Verificar `git reflog`
2. Verificar `git stash list`
3. Verificar `git diff HEAD`
4. Verificar lixeira do SO
5. NUNCA desistir sem verificar todas as opcoes acima

### Acao Alternativa em Falha

Se uma tarefa falha, NAO repetir a mesma acao. Tentar:
- `read_file` para entender o estado atual antes de `edit_file`/`refactor_code`
- `list_directory` para descobrir arquivos disponiveis
- `run_tests` antes de `refactor_code` para entender falhas
- Consultar `negocios` antes de planejar mudancas

### Reflexao Pos-Missao

Apos cada missao (bem-sucedida ou falha):
1. Consolidar o que funcionou e o que nao funcionou
2. Persistir aprendizados em tree/licoes.md
3. Atualizar tree/delegacao.md com novos padroes
4. Nao repetir erros de missoes anteriores
