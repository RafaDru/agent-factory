# Historico de Evolucao — Agent Factory Platform Team

Este arquivo documenta a evolucao da plataforma, missoes executadas,
decisoes arquiteturais passadas e aprendizados tecnicos especificos
(nao de orquestracao). Serve como memoria de longo prazo para
evitar que conhecimento se perca em compactacoes de contexto.

---

## Arquitetura de Comunicacao

### Fase 1 — In-Process (original)
Coordenador instanciava subordinados como objetos Python e chamava
metodos diretamente. Simples, mas sem isolamento.

### Fase 2 — Hibrido MCP + Event Bus (atual)
Coordenador delega tarefas via RabbitMQ (`task.run.{agent_id}`).
Cada agente roda em seu proprio `AgentRuntime` com LLM autonomo.
MCP Gateway tenta Event Bus primeiro, fallback in-process.

## Decisoes Arquiteturais

- **RabbitMQ como espinha dorsal**: exchanges + routing keys para
  comunicacao agente-agente. RPC pattern com filas exclusivas de reply.
- **AgentRuntime**: processo separado que consome fila, carrega agente,
  executa task e publica resultado. Desacoplamento total.
- **MCP Gateway**: bridge entre o mundo externo (IDE/LLM) e o Event Bus.
  Mantem compatibilidade com ferramentas MCP tradicionais.
- **SSE e por-processo**: eventos emitidos por runtimes RabbitMQ nao
  chegam ao dashboard (issue #13 - pendente).

## Missoes Executadas

### missao-listar-arquivos-projeto-seguida-fazer-uma
- Listar arquivos + pesquisar design systems
- 2/2 tarefas aceitas. DAG linear simples.

### missao-adicionar-docstring-google-style-todas-funcoes
- Adicionar docstrings em src/eventbus/amqp.py
- 6/6 tarefas aceitas. Licao: revisao deve vir antes do commit.

### missao-modificar-metodo-_delegate-src-agents-coordinator
- Modificar _delegate() para usar RabbitMQ quando disponivel
- 6/6 tarefas aceitas. Event Bus integrado ao fluxo de delegacao.

### missao-analisar-pontos-abaixo-classificar-cada-como
- Classificar bugs/melhorias e priorizar
- 2/4 tarefas aceitas. Negocios falhou porque coordinator nao o listava.

### missao-analisar-backlog-projeto-afp-team-validar
- Analisar backlog, validar com negocios, pesquisar design systems
- 1/6 tarefas aceitas. Dev falhou ao ler backlog.md inexistente.

## Licoes Tecnicas (Especificas de Implementacao)

### Flexbox scroll
Elementos com `overflow-y:auto` precisam de `min-height:0` no flex child
quando o parent tem `overflow:hidden`.

### async/await
Toda funcao que usa `await` precisa ser declarada `async`.

### Event delegation
`document.addEventListener('click')` com `closest()` para elementos
dinamicos. Deve estar no escopo global, nao aninhado em outra funcao.

### Timestamps
`datetime.utcnow()` retorna naive (sem tzinfo). JS interpreta ISO sem
timezone como LOCAL. Usar `datetime.now(timezone.utc)` e anexar 'Z'.

### Interaction Flow
`switchView()` deve carregar eventos historicos de `/api/events` para
popular `agentState.events`.

### Dashboard scope bug
IIFE precisa ser fechada apos todas as funcoes. `})();` no final
do segundo `<script>`.

## Issues e Melhorias Pendentes

- #13: SSE por-processo nao capta eventos de runtimes RabbitMQ
- #14: Coordinator deve delegar para negocios (resolvido - prompt dinamico)
- #15: Validar ciclo reflexao -> aprendizado na arvore (concluido)
- Interaction Flow: redesign multi-turn (prototipo do designer existe)
