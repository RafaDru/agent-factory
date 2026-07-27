# Licoes — coordenador — AFP-Team

## Consolidado

### missao-010-refresh-tasks-grupos-colapsaveis-timer
- **Objetivo**: E-010 UI Refresh: tasks B-H — grupos colapsaveis, timer condicional, breadcrumb, modal LLM, responsi
- **Resultado**: 0/7 tarefas aceitas
- **Falhas**: timer-condicional, breadcrumb, grupos-colapsaveis, responsividade, modal-llm
- **Reflexao**: **Planejamento (DAG):** O DAG atribuiu ações de implementação (`implement_feature`) ao agente `designer`, cujas capacidades são exclusivamente de design e prototipação. Isso revela uma falha de mapeamento: o planejamento não respeitou os limites de cada agente. Para futuras missões, o DAG deve ser v


### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 3/3 tarefas aceitas
- **Reflexao**: **Planejamento (DAG):** A missão foi estruturada como três tarefas independentes (listar-agents, listar-dashboard, validar-server), executadas em paralelo. O DAG estava correto para o objetivo de testar o mecanismo RPC — não havia dependências entre listagem e validação, e a execução simultânea foi 


### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 0/3 tarefas aceitas
- **Falhas**: listar-agents, listar-dashboard
- **Reflexao**: A missão falhou em suas etapas de desenvolvimento, com ambos os agentes `dev` retornando `failure` sem detalhes, sugerindo que o teste RPC não estava operacional ou os agentes não conseguiram executar as listagens. O DAG parece ter dependência implícita: a tarefa de QA foi ignorada (`skipped`) prova


### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 0/3 tarefas aceitas
- **Falhas**: listar-agents, listar-dashboard
- **Reflexao**: A missão revelou fragilidades no planejamento e na execução. O DAG previa que as tarefas de listagem (dev) fossem pré-requisito para a validação (qa), mas ambas falharam sem detalhes, indicando que os agentes dev não conseguiram sequer iniciar a operação — possivelmente por falta de acesso ao ambien


### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 0/3 tarefas aceitas
- **Falhas**: listar-agents, listar-dashboard
- **Reflexao**: **Planejamento:** O DAG previa duas tarefas de listagem executadas por agentes `dev` e uma validação por `qa` dependente do sucesso delas. A estrutura estava correta em teoria, mas a falha generalizada dos `dev` sugere que faltou uma etapa de verificação de pré-requisitos (ex.: diretórios existentes


### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 0/3 tarefas aceitas
- **Falhas**: listar-agents, listar-dashboard
- **Reflexao**: A missão foi estruturada com um DAG simples: dois agentes dev em paralelo (listar-agents e listar-dashboard) e, na sequência, o agente qa (validar-server). O planejamento parece correto para um teste de RPC, mas a falha simultânea de ambos os devs com detalhes vazios indica que o problema não estava


### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 0/3 tarefas aceitas
- **Falhas**: listar-agents, listar-dashboard
- **Reflexao**: **Planejamento (DAG):** O DAG estava correto ao encadear as tarefas de listagem (dev) antes da validação (qa). A falha nas tarefas de desenvolvimento bloqueou corretamente a execução da validação, que foi ignorada (skipped). A dependência funcionou como esperado, preservando a integridade do fluxo.



### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 0/3 tarefas aceitas
- **Falhas**: listar-agents, listar-dashboard
- **Reflexao**: **Planejamento e delegação:** O DAG previa duas tarefas de desenvolvimento (`listar-agents` e `listar-dashboard`) seguidas por uma validação de QA (`validar-server`). A atribuição ao agente `dev` para as tarefas de listagem foi adequada, mas a falha idêntica em ambas revela um problema sistêmico na 


### missao-listar-diretorios-validar-sintaxe-teste-rpc
- **Objetivo**: Listar diretorios e validar sintaxe (teste RPC)
- **Resultado**: 0/3 tarefas aceitas
- **Falhas**: listar-agents, listar-dashboard
- **Reflexao**: A missão foi estruturada com um DAG simples e coerente: listar diretórios (agentes dev) e validar sintaxe (agente qa). A falha não decorreu de um planejamento incorreto, mas de um erro técnico no código do agente dev ao tentar acessar um atributo inexistente (`output`) no objeto `TaskOutput`. A dele


### missao-cross-project-isolation-e-cache
- **Acao**: plan_and_execute
- **Resumo**: Corrigir poluicao de estado entre projetos no dashboard, adicionar Cache-Control, corrigir bugs de template
- **Licoes**:
  - **Poluicao de estado**: qualquer estado global indexado por ID de agente deve usar `projectId:agentId` como chave
  - **Cache-Control**: sempre definir `Cache-Control: no-cache` em respostas HTML de SPA
  - **TDZ**: em arquivos grandes, manter declaracoes no topo ou revisar ordem de definicao
  - **Fallback in-process**: o fallback in-process e fragil para execucao real; so e confiavel para planejamento

### missao-remover-interaction-flow-timeline-panel-console
- **Acao**: plan_and_execute
- **Resumo**: Remover Interaction Flow, manter apenas Mission Control — 1/7 tarefas aceitas
- **Licao**: nao havia contingencia para falhas em etapas iniciais de levantamento

### missao-arquivo-src-dashboard-index-html-foi
- **Acao**: plan_and_execute
- **Resumo**: Restaurou ~70KB perdidos por git checkout — 12/12 tarefas aceitas
- **Licao**: DAG linear (designer → dev → QA) foi adequado para missao de recuperacao

### missao-remover-botao-detalhes-mission-control-dashboard
- **Acao**: plan_and_execute
- **Resumo**: Falhou multiplas vezes porque o dev pediu file_path/old_string/new_string que o coordenador nao forneceu
- **Licao**: sempre passar parametros concretos (file_path, old_string, new_string) ao delegar para dev

### missoes anteriores (falhas parciais)
- Varias missoes com falhas por planejamento inadequado (DAG linear rigido, acoes indisponiveis)
- Licao: sempre validar se as acoes necessarias existem no agente antes de delegar
- Licao: se uma tarefa falha, o coordenador deve tentar acao ALTERNATIVA, nao repetir a mesma acao
- Licao: se o RPC timeout nao recebe reply, tentar acao diferente (ex: read_file antes de edit_file)
