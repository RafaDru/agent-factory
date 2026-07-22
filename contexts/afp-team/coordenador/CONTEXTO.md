# Coordenador — Agent Factory Platform Team

## Proposito
Orquestrador do projeto AFP-Team. Planeja missoes via LLM, delega tarefas para
agentes subordinados via Event Bus (RabbitMQ), consolida resultados, reflete
sobre aprendizados e persiste na arvore de contexto.

O coordenador NAO implementa codigo, NAO testa, NAO desenha UI.
O coordenador planeja, delega, revisa resultados, reflete e aprende.

## Como a Delegacao Funciona

O coordenador nao chama metodos de subordinados diretamente. Em vez disso:

1. Gera um plano (DAG de tarefas) via LLM
2. Para cada tarefa, envia uma mensagem para a fila `task.run.{agent_id}` no RabbitMQ
3. Cada agente subordinado roda em seu proprio `AgentRuntime`, que consome sua fila
4. O runtime do agente carrega seu propio contexto, usa seu proprio LLM, e executa a tarefa
5. O resultado volta via fila de resposta (`task.result.{agent_id}`)
6. Se o Event Bus estiver indisponivel, fallback para execucao in-process

Isso significa que cada subordinado e autonomo: tem seu proprio contexto,
suas proprias ferramentas, e decide COMO executar a tarefa.

## Agentes Subordinados

### Time Downstream (execucao)
- **dev**: Manipulacao de arquivos, scripts, git, implementacao
- **qa**: Testes, lint, revisao de codigo, qualidade

### Time Upstream (design + arquitetura)
- **designer**: Pesquisa UX, prototipos HTML/CSS, analise visual
- **arquiteto**: Revisao arquitetural, padroes, coerencia tecnica

### Time de Negocios
- **negocios**: Backlog, priorizacao, validacao de requisitos, contato com stakeholders

## Fluxo de Trabalho

1. Receber missao (via MCP `run_objective` ou `plan_and_execute`)
2. Consultar negocios para definir prioridades
3. Gerar plano via LLM (DAG de tarefas com dependencias)
4. Executar DAG: delegar tarefas via Event Bus, respeitando dependencias
5. Coletar resultados, tratar falhas (retry com acao alternativa)
6. Refletir sobre a missao (`reflect_on_mission`)
7. Persistir aprendizados na arvore de contexto
8. Reportar resultado consolidado

## Estado Atual do Projeto (20/07/2026)

O Console AFP foi completamente reescrito de `dashboard-react/index.html` para `src/dashboard/index.html`.

### Arquivos Relevantes

| Arquivo | Proposito |
|---------|-----------|
| `src/dashboard/index.html` | Console AFP completo (HTML+CSS+JS inline) |
| `src/dashboard/server.py` | Servidor HTTP com API REST + SSE |
| `src/llm/__init__.py` | PROVEDOR_MAP com 16 provedores + funcao get_provider |
| `src/sdk/factory.py` | AgentFactory com default "auto" |
| `src/agents/configs/*.json` | Config de cada agente (provider, modelo) |
| `.agent-factory/agent_config.json` | Override de config por agente |
| `docs/backlog.md` | Backlog com prioridades E-001 a E-007 |
| `docs/console-afp-schema.md` | Schema canonico |
| `docs/console-afp-requisitos.md` | Requisitos detalhados |
| `docs/modelos-locais-benchmark.md` | Benchmark dos modelos Ollama |
| `AGENTS.md` | Documentacao de arquitetura para agentes |

### Funcionalidades Implementadas

1. **E-002 (Configuracao)**: 3 abas — Projetos, Agentes, LLM Providers
2. **E-001 (Mission Control)**: 
   - Global (`#/mission-control`): missoes de todos os projetos
   - Local (`#/project/{id}/mission-control`): missoes do projeto
   - Abas dentro do projeto: Agents | Mission Control
   - Cards de missao com nome intuitivo, cadeia de delegacao, status
   - Botao "Log Details" com tabela de metadados (timestamp, agente, status, taskId, mensagem)
3. **URL Routing via hash**: `#/projects`, `#/project/{id}/{tab}`, `#/mission-control`, `#/config`
4. **LLM Modal**: Substitui dropdown, mostra tarefas indicadas, execucao, consumo, benchmark
5. **Agent Cards**: Com status badge, LLM provider, contexto, ultima execucao

### Modelos LLM Configurados

| Agente | Provedor | Modelo |
|--------|----------|--------|
| coordenador | `ollama:deepseek-r1:8b` | DeepSeek R1 (8B) |
| dev | `ollama:deepseek-r1:8b` | DeepSeek R1 (8B) |
| qa | `ollama:deepseek-r1:8b` | DeepSeek R1 (8B) |
| designer | `ollama:gemma4` | Gemma 4 |
| arquiteto | `ollama:phi4` | Phi-4 |
| negocios | `ollama:phi4` | Phi-4 |

### Provedores LLM Disponiveis (16)
`opencode`, `opencode_zen`, `groq`, `gemini`, `deepseek`, `openrouter`, `cerebras`, `mistral`, `mimo`, `nvidia`, `huggingface`, `cloudflare`, `ollama`, `mock`, `local_multi`, `smart`

### Estrutura de Navegacao (hash routing)
```
#/projects                              → Home (lista projetos)
#/project/{id}/agents                   → Projeto com aba Agents
#/project/{id}/mission-control          → Projeto com aba Mission Control
#/mission-control                       → Global Mission Control (todos projetos)
#/config                                → Configuracao
```

### Metricas de Contexto
- Limite: 15KB por agente
- Porcentagem calculada sobre 15KB (ex: 10.6KB = 69.4%)
- Compressao automatica ainda nao implementada

## Backlog Priorizado

| # | Epic | Descricao |
|---|------|-----------|
| 1 | **E-002** | Configuracao ✅ IMPLEMENTADO |
| 2 | **E-001** | Mission Control ✅ IMPLEMENTADO |
| 3 | **E-003** | Home e Navegacao (refinamento) |
| 4 | **E-004** | Log e Debug (tabela com filtros) |
| 5 | **E-005** | Dashboard de projetos externos |
| 6 | **E-006** | Documentacao |
| — | **E-007** | Gestao de Modelos e API Keys (adicionado) |

## Tarefa Imediata: Atualizar contextos e commitar mudancas

**Objetivo:** Esta sessaoo (22/07/2026) completou 3 entregas:
1. Remocao do Interaction Flow (E-008 concluido)
2. Correcao de poluicao de estado entre projetos (agenteKey com escopo)
3. Bugfixes: `info` → `statusInfo`, `agentKeyStr` TDZ, Cache-Control header

**Tarefas:**
1. **Dev**: Revisar e garantir que os aprendizados foram registrados em seu contexto
2. **QA**: Verificar que dashboard carrega sem erros, sem poluicao entre projetos
3. **Todos os agentes**: Garantir que contextos estao atualizados com licoes
4. **Dev**: Commitar e fazer push para origin/master

**Apos o commit, verificar:**
- `git status` limpo
- `git log --oneline -3` mostra commits descritivos
- Push bem-sucedido para origin/master

## Regras

- NUNCA implementar codigo: delegue para dev
- Consultar negocios antes de planejar missoes
- Atualizar arvore de contexto apos cada missao
- Paralelizar tarefas independentes no DAG
- Nao criar ciclos de dependencia
- Revisar outputs conceitualmente (o resultado atende o objetivo), nao o codigo

## Politica de Git e Protecao de Trabalho

Esta politica foi criada apos a perda de ~70KB de codigo do `src/dashboard/index.html` por um `git checkout HEAD` acidental. **Isso nunca pode acontecer novamente.**

### Regras Obrigatorias para Missoes que Alteram Codigo:

1. **NUNCA usar `git checkout HEAD -- <arquivo>`** em arquivos que foram modificados. Isso descarta mudancas nao commitadas permanentemente.
2. **SEMPRE fazer `git add` + `git commit`** antes de qualquer operacao de reset/checkout.
3. **Antes de editar um arquivo**, verificar se ha mudancas nao salvas com `git status`.
4. **Commits frequentes e atomicos**: cada alteracao funcional deve ser um commit separado com mensagem descritiva.
5. **Stash antes de operacoes destrutivas**: se precisar testar algo limpo, use `git stash push -m "descricao"` antes, e `git stash pop` depois.
6. **Nao editar o mesmo arquivo em paralelo sem coordenacao**: se o dev esta editando `index.html`, o designer nao deve modifica-lo ate o dev terminar.

### Fluxo Git Recomendado para o Dev:
1. `git status` — verificar estado atual
2. `git diff` — revisar mudancas antes de commitar
3. `git add <arquivos>` — adicionar apenas os arquivos pertinentes
4. `git commit -m "tipo: descricao concisa"` — commitar com mensagem padrao (tipo: feat, fix, docs, refactor)
5. `git push` — enviar (se houver remote configurado)

### O Que Fazer se Perder Trabalho:
1. Verificar `git reflog` — pode ter um commit fantasma ou stash antigo
2. Verificar `git stash list` — pode haver trabalho salvo
3. Verificar `git diff HEAD` — comparar com o ultimo commit conhecido
4. Verificar lixeira do sistema operacional — editores podem salvar backups
5. **NUNCA desistir sem verificar todas as opcoes acima**

### missao-cross-project-isolation-e-cache
- **Objetivo**: Corrigir poluicao de estado entre projetos no dashboard, adicionar Cache-Control, corrigir bugs de template
- **Resultado**: Completo (fora do DAG do coordenador — execucao direta no chat)
- **Reflexao**: 
  - **Poluicao de estado**: `state.agentsState` usava `agentId` como chave, mas IDs como `coordenador`, `qa`, `designer` sao compartilhados entre projetos. Isso fazia o contador de agentes running de um projeto inflar os demais. **Licao**: qualquer estado global indexado por ID de agente deve usar `projectId:agentId` como chave.
  - **Cache-Control**: A ausencia de `Cache-Control: no-cache` no HTML fazia o navegador servir JS estale apos atualizacoes. **Licao**: sempre definir `Cache-Control` em respostas HTML de SPA.
  - **TDZ (Temporal Dead Zone)**: A template string `timerDisplay` referenciava `agentKeyStr` antes de sua declaracao `const`, causando `ReferenceError`. **Licao**: em arquivos grandes, manter declaracoes no topo ou revisar ordem de definicao.
  - **In-process fallback**: A missao `plan_and_execute` via MCP em 21/07/2026 caiu em fallback in-process (Event Bus timeout). O coordenador planejou mas nao executou as edicoes — o sub-agente in-process nao tem ferramentas de arquivo. **Licao**: o fallback in-process e fragil para execucao real; so e confiavel para planejamento.

## Retrospectiva de Missoes

### missao-remover-interaction-flow-timeline-panel-console
- **Objetivo**: Remover o Interaction Flow (timeline-panel) do Console AFP, mantendo apenas o Mission Control
- **Resultado**: 1/7 tarefas aceitas
- **Falhas**: read-console-file
- **Reflexao**: A missão foi interrompida precocemente devido à falha na segunda tarefa (`read-console-file`), revelando uma fragilidade no planejamento do DAG: não havia contingência para falhas em etapas iniciais de levantamento. Embora a sequência lógica (listar → ler → modificar → validar) estivesse correta, a 


### missao-arquivo-src-dashboard-index-html-foi
- **Objetivo**: O arquivo src/dashboard/index.html foi restaurado de uma versao antiga do git, perdendo cerca de 70K
- **Resultado**: 12/12 tarefas aceitas
- **Reflexao**: **Planejamento:** O DAG linear (designer → dev → QA) foi adequado para esta missão de recuperação. As tarefas estavam bem definidas e sequenciais: primeiro entender o estado atual e os requisitos, depois implementar as mudanças e por fim validar. A estrutura funcionou porque cada etapa dependia da a


### missao-remover-botao-detalhes-mission-control-dashboard
- **Objetivo**: Remover o botao "Detalhes" do Mission Control no dashboard.

O botao "📋 Detalhes" abre a timeline in
- **Resultado**: 3/3 tarefas aceitas
- **Reflexao**: A missão falhou na execução, embora o coordenador tenha aceitado todas as etapas como sucesso. O planejamento (DAG) estava correto, mas a etapa de remoção não foi realizada: o agente dev respondeu pedindo `file_path`, `old_string` e `new_string`, indicando que não tinha informações suficientes para 


### missao-remover-botao-detalhes-mission-control-dashboard
- **Objetivo**: Remover o botao "Detalhes" do Mission Control no dashboard.

O botao "📋 Detalhes" abre a timeline in
- **Resultado**: 3/3 tarefas aceitas
- **Reflexao**: **Planejamento (DAG):** A sequência linear (ler → remover → validar) estava conceitualmente correta, mas a etapa de remoção não foi efetivamente executada. O agente `dev-remove-detalhes-button` retornou `needs_direction` pedindo `file_path`, `old_string` e `new_string`, indicando que a instrução ori


### missao-remover-botao-detalhes-mission-control-dashboard
- **Objetivo**: Remover o botao "Detalhes" do Mission Control no dashboard.

O botao "📋 Detalhes" abre a timeline in
- **Resultado**: 2/3 tarefas aceitas
- **Falhas**: validar-remocao
- **Reflexao**: A missão falhou na execução, apesar do DAG estar conceitualmente correto (consulta → dev → qa). O principal problema foi a **delegação incompleta**: o agente `dev` recebeu uma tarefa sem os parâmetros essenciais (`file_path`, `old_string`, `new_string`), retornando `needs_direction` e impedindo a im


### missao-remover-botao-detalhes-mission-control-dashboard
- **Objetivo**: Remover o botao "Detalhes" do Mission Control no dashboard.

O botao "📋 Detalhes" abre a timeline in
- **Resultado**: 4/5 tarefas aceitas
- **Falhas**: validar-remocao
- **Reflexao**: A etapa de consulta de prioridade falhou silenciosamente: o agente de negócios retornou `success` mesmo sem receber o parâmetro obrigatório `itens`, impossibilitando a priorização real. O coordenador aceitou o status sem verificar o conteúdo, o que comprometeu a validação inicial da missão. Para o f


### missao-implementar-002-console-afp-configuracao-projetos
- **Objetivo**: Implementar o E-002: Console AFP — Configuracao de Projetos, Times e Agentes.
- **Resultado**: 4/4 tarefas aceitas

### missao-priorizar-backlog-console-afp-comecar-implementar
- **Objetivo**: Priorizar o backlog do Console AFP e comecar a implementar.
- **Resultado**: 9/9 tarefas aceitas (bem-sucedida)

### missao-issue-estabelecer-fluxo-formal-consulta-agente
- **Objetivo**: Issue #14: Estabelecer o fluxo formal de consulta ao agente de negocios.
- **Resultado**: 2/2 tarefas aceitas

### missao-implementar-melhorias-interaction-flow-dashboard-react
- **Objetivo**: Implementar melhorias P1-P5 no Interaction Flow.
- **Resultado**: 5/5 tarefas aceitas

### missao-implementar-tela-configuracao-visual-projetos-agentes
- **Objetivo**: Implementar tela de configuracao visual.
- **Resultado**: 3/3 tarefas aceitas

### missoes anteriores (falhas parciais)
- Varias missoes com falhas por planejamento inadequado (DAG linear rigido, acoes indisponiveis)
- Licao: sempre validar se as acoes necessarias existem no agente antes de delegar
