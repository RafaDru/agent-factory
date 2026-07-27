# Delegacao — coordenador — AFP-Team

## Como a Delegacao Funciona

O coordenador nao chama metodos de subordinados diretamente. Em vez disso:

1. Gera um plano (DAG de tarefas) via LLM
2. Para cada tarefa, envia uma mensagem para a fila `task.run.{agent_id}` no RabbitMQ
3. Cada agente subordinado roda em seu proprio `AgentRuntime`, que consome sua fila
4. O runtime do agente carrega seu propio contexto, usa seu proprio LLM, e executa a tarefa
5. O resultado volta via fila de resposta (`task.result.{agent_id}`)
6. Se o Event Bus estiver indisponivel, fallback para execucao in-process

Isso significa que cada subordinado e autonomo: tem seu propio contexto,
suas proprias ferramentas, e decide COMO executar a tarefa.

## Padroes de Delegacao

- Tasks de leitura vao para `dev`
- Tasks de validacao/teste vao para `qa`
- Tasks de prototipo/UX vao para `designer`
- Tasks de priorizacao/requisitos vao para `negocios`
- Tasks de revisao arquitetural vao para `arquiteto`

## RPC entre Coordinator e Runtime

Quando o coordenador delega uma tarefa via Event Bus, ele usa RPC:

1. Cria uma fila exclusiva no RabbitMQ
2. Publica a tarefa em `task.run.{agent_id}` com `reply_to` apontando para `agent.reply.{queue_name}`
3. Aguarda o resultado via `process_data_events()` no mesmo canal
4. Se timeout, retry com acao ALTERNATIVA (nao a mesma acao)
