# Agent Factory Platform

**Orquestrador de agentes de IA autonomes.** Delega objetivos para agentes
especializados via Event Bus (RabbitMQ), cada um com seu proprio contexto
e LLM. Painel em tempo real, MCP Server para integracao com IDEs/LLMs.

> Beta — v3.0.0

---

## O que e e como opera

A AFP e um orquestrador. Ela recebe um objetivo em linguagem natural e
delega a execucao para agentes especializados que trabalham autonomamente.

```
Humano / LLM (OpenCode, Claude, Cursor, etc.)
  │
  ▼  "run_objective(project='...', objective='...')"
AFP MCP Server (porta 8081)
  │
  ├── Coordenador (built-in, codigo proprio)
  │     │  1. Recebe objetivo
  │     │  2. Gera plano (DAG de tarefas) via LLM
  │     │  3. Delega para workers via RabbitMQ
  │     │
  │     ├──► RabbitMQ ──► AgentRuntime (processo separado)
  │     │     task.run.dev           │  Carrega CONTEXTO.md
  │     │     task.run.qa            │  Usa seu proprio LLM
  │     │     task.run.designer      │  Executa e responde
  │     │     ...                    │
  │     │  4. Consolida resultados
  │     │  5. Reflete e persiste aprendizado
  │     │
  │     └──► Resultado estruturado
  │
  └── Dashboard (http://localhost:8082)
        Eventos em tempo real via SSE
```

## Componentes

| Componente | Descricao |
|---|---|
| **Coordenador** | Unico componente com codigo proprio. Planeja a DAG, delega via Event Bus, reflete e aprende. |
| **Workers** | Agentes genericos criados pelo `AgentFactory`. Identidade e comportamento vêm do `CONTEXTO.md`. |
| **AgentRuntime** | Processo separado que consome fila RabbitMQ, carrega o agente, executa a tarefa e publica o resultado. |
| **RabbitMQ** | Espinha dorsal da comunicacao: filas `task.run.{agent_id}` para delegacao, `task.result.{agent_id}` para resposta. |
| **MCP Server** | Gateway externo (SSE na porta 8081). Expoe `run_objective`, `run_agent`, etc. como ferramentas MCP. |
| **Dashboard** | UI web em tempo real (porta 8082). Missoes, eventos, status dos agentes. |

## Papeis

| Papel | Origem | Natureza |
|---|---|---|
| **Coordenador** | AFP (built-in) | Codigo fixo (`src/agents/coordinator.py`). Logica de DAG, delegacao, reflexao. |
| **Workers** (dev, qa, designer, negocios, arquiteto, etc.) | Projeto do usuario | Contexto declarativo (`CONTEXTO.md`). Um unico `DeclarativeAgent` generico. |

O coordenador e **parte da plataforma**, nao configurado pelo usuario.
Os workers sao **definidos pelo usuario** — ele cria os CONTEXTO.md com
o proposito e as acoes de cada papel.

---

## Usando a Plataforma com um Projeto Externo

### 1. Configure o projeto

Em `contexts/meu-projeto/project.json`:

```json
{
  "project_id": "meu-projeto",
  "project_name": "Meu Projeto",
  "working_dir": "/caminho/para/meu/projeto",
  "agents": [
    {
      "agent_id": "dev",
      "context_file": "agentes/dev/CONTEXTO.md",
      "llm_provider": "auto"
    },
    {
      "agent_id": "qa",
      "context_file": "agentes/qa/CONTEXTO.md",
      "llm_provider": "auto"
    }
  ]
}
```

### 2. Crie os contextos dos agentes

`agentes/dev/CONTEXTO.md`:
```markdown
# Dev — Meu Projeto

## Proposito
Agente de desenvolvimento. Opera arquivos, scripts e git.

## Acoes Disponiveis
| Acao | Descricao |
|------|-----------|
| read_file | Le conteudo de um arquivo |
| write_file | Escreve conteudo em arquivo |
| run_script | Executa script Python |
| run_git | Executa comandos git |
```

### 3. Inicie a plataforma

```bash
docker compose up -d rabbitmq   # Event Bus
python start_agent_factory.py   # MCP + Dashboard
python -m src.agents.runtime src.agents.factory_dev.DevAgent dev meu-projeto
```

### 4. Envie um objetivo

```bash
# Via MCP (do OpenCode/Claude/Cursor)
run_objective(project_id="meu-projeto", objective="Adicionar testes no modulo X")
```

---

## Estrutura de Diretorios

```
agent-factory/
├── src/                    # Codigo da plataforma
│   ├── agents/
│   │   ├── coordinator.py  # Unico com codigo proprio
│   ├── sdk/
│   │   ├── base.py         # StandardBaseAgent
│   │   └── factory.py      # AgentFactory (cria workers genericos)
│   ├── eventbus/
│   │   └── amqp.py         # RabbitMQ: publisher, consumer, RPC
│   ├── mcp/
│   │   └── server.py       # MCP Gateway (SSE)
│   └── registry.py         # Projetos e referencias
├── contexts/
│   ├── afp-team/           # Time meta (come a propria comida)
│   └── seu-projeto/        # Seus agentes
├── .agent-factory/         # Dados gerados (eventos, missoes, arvore)
├── docker-compose.yml      # RabbitMQ
└── AGENTS.md               # Fluxo de delegacao recursiva
```

## A Estrutura de Pastas do Projeto do Usuario "Pouco Importa"

A unica exigencia e que cada agente tenha seu `CONTEXTO.md` acessivel
no caminho indicado pelo `project.json`. A arvore de diretorios ao
redor e irrelevante:

```
/qualquer/pasta/
  ├── docs/meu_time/dev/CONTEXTO.md
  ├── config/qa.md                  ← so renomear a referencia
  └── qualquer/pasta/negocios.md

project.json so precisa apontar:
  {
    "agent_id": "negocios",
    "context_file": "qualquer/pasta/negocios.md"
  }
```

## Como Funciona a Execucao de um Worker

1. `AgentFactory.build()` le as configuracoes do `project.json`
2. Em tempo de execucao, carrega o `CONTEXTO.md` como identidade
3. O `AgentRuntime` recebe uma task via RabbitMQ
4. Usa o LLM configurado para decidir como executar
5. Toda evolucao (licoes, padroes) persiste em `.agent-factory/[projeto]/tree/`

Cada execucao soma: **identidade original** (CONTEXTO.md) + **memoria acumulada** (arvore de contexto).

---

## MCP Server

```bash
python start_agent_factory.py --mcp
# Servidor em http://127.0.0.1:8081/sse
# Endpoint POST: /messages/?session_id=X
```

### Tools

| Tool | Descricao |
|------|-----------|
| `list_projects` | Lista projetos registrados |
| `run_objective` | Envia objetivo ao coordenador |
| `run_agent` | Executa tarefa em um agente |
| `read_events` | Le eventos recentes |

Veja [AGENTS.md](AGENTS.md) para o fluxo completo de delegacao.

---

## Roadmap

- [ ] Tela de configuracao visual: declarar estrutura de projeto + times +
  agentes via UI, com explorer para navegar ate os `CONTEXTO.md` de cada
  agente e exibir seu conteudo de forma humanizada
- [ ] Documentacao oficial em site
- [ ] CLI tooling
- [ ] Plugin system

---

## License

MIT
