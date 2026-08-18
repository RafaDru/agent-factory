# Arquitetura — Agent Factory Platform

> Documento canônico da plataforma AFP.  
> Para operação diária de agentes IA, veja [AGENTS.md](../AGENTS.md).  
> Para schema do Console AFP, veja [console-afp-schema.md](console-afp-schema.md).

---

## Princípio fundacional

**A Factory é plataforma de execução e comunicação — os agentes moram nos projetos de origem.**

| Responsabilidade | Quem |
|---|---|
| Orquestrar, rotear mensagens, expor MCP, rotear LLM, persistir eventos | **Agent Factory (este repo)** |
| Identidade, propósito, ações, aprendizado de domínio | **Projeto do usuário** (`CONTEXTO.md`, configs, código opcional) |
| Produto de negócio (PTA, solar, impressora 3D…) | **Projeto registrado** — north star do usuário, não do Factory |

A AFP **não** é um repositório de agentes por domínio. Ela **referencia** agentes externos e **executa** sob demanda ([`src/loader.py`](../src/loader.py), [`src/registry.py`](../src/registry.py)).

Histórico da separação: [historico/2026-06-26_refatoracao-separacao-agentes.md](historico/2026-06-26_refatoracao-separacao-agentes.md).

---

## O que a AFP é (e não é)

### É

- **Runtime de organização agentica** — coordenador + workers + bus + MCP + dashboard
- **Gateway MCP** para IDEs (Cursor, OpenCode, Claude Code)
- **Roteador de LLM** com fallback entre provedores free e locais
- **Console operacional** (Mission Control, Live Stream, Config)

### Não é

- IDE agentica (Cursor, Copilot)
- Framework de grafo/LangGraph (CrewAI, LangGraph)
- Produto vertical pronto (PTA, Open Health, etc.)
- Catálogo fixo de papéis dev/qa/designer como modelo de produto — isso é **dogfood** do time AFP-Team

---

## Visão em camadas

```
┌─────────────────────────────────────────────────────────────┐
│  Camada externa — IDE / Humano                              │
│  OpenCode · Cursor · Claude Code · Dashboard (browser)      │
└───────────────────────────┬─────────────────────────────────┘
                            │ MCP (SSE :8081) · REST/SSE (:8082)
┌───────────────────────────▼─────────────────────────────────┐
│  Camada plataforma — Agent Factory                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ MCP Server  │  │ Coordinator  │  │ SmartRouter (LLM)   │ │
│  │ run_objective│  │ plan + DAG   │  │ groq/zen/ollama/…  │ │
│  └──────┬──────┘  └──────┬───────┘  └─────────────────────┘ │
│         │                 │                                   │
│         │     ┌───────────▼───────────┐                       │
│         │     │ Event Bus (RabbitMQ)  │  ← Standard           │
│         │     │ task.run.{agent_id}   │                       │
│         │     └───────────┬───────────┘                       │
│         │                 │ fallback in-process  ← Lite         │
│         │     ┌───────────▼───────────┐                       │
│         │     │ AgentRuntime / Worker │                       │
│         │     │ DeclarativeWorker     │                       │
│         │     └───────────┬───────────┘                       │
└─────────────────────────┼─────────────────────────────────────┘
                          │ carrega identidade + executa
┌─────────────────────────▼─────────────────────────────────────┐
│  Camada projeto — mora FORA ou REFERENCIADA pelo Factory      │
│  contexts/{projeto}/ · CONTEXTO.md · tree/ · .agent-factory/  │
│  (opcional) agentes/*.py no working_dir do projeto            │
└───────────────────────────────────────────────────────────────┘
```

---

## Componentes da plataforma

| Componente | Código | Função |
|---|---|---|
| **Coordenador** | [`src/agents/coordinator.py`](../src/agents/coordinator.py) | Único agente com lógica Python fixa na plataforma. Recebe objetivo, gera DAG via LLM, delega, consolida, reflete. |
| **Worker genérico** | [`src/agents/worker.py`](../src/agents/worker.py) + [`src/sdk/factory.py`](../src/sdk/factory.py) | `DeclarativeWorker` — identidade vem de `configs/{id}.json` + `CONTEXTO.md`. |
| **AgentRuntime** | [`src/agents/runtime.py`](../src/agents/runtime.py) | Processo que consome fila (Standard) ou responde in-process (Lite). |
| **Event Bus** | [`src/eventbus/amqp.py`](../src/eventbus/amqp.py) | RabbitMQ: RPC, filas `task.run.*` / `task.result.*`. |
| **MCP Server** | [`src/mcp/server.py`](../src/mcp/server.py) | Ferramentas `run_objective`, `run_agent`, `list_projects`, `read_events`. |
| **Dashboard / Console AFP** | [`dashboard-react/`](../dashboard-react/) | UI :8082 — projetos, agentes, Mission Control, config LLM. |
| **Registry** | [`src/registry.py`](../src/registry.py) | Registro de projetos e referências a agentes. |
| **Loader** | [`src/loader.py`](../src/loader.py) | Import dinâmico de agentes sob demanda. |
| **LLM Router** | [`src/llm/__init__.py`](../src/llm/__init__.py) | `get_provider("auto")` — Groq, OpenCode Zen, Ollama, OpenRouter, etc. |

---

## Onde vivem os agentes

### Identidade (obrigatório)

```
contexts/{project_id}/{agent_id}/
├── CONTEXTO.md      ← propósito, ações, exemplos (identidade versionada)
├── INDEX.md         ← índice humano
└── tree/            ← aprendizado acumulado (features, bugs, lições…)
```

O caminho exato do `CONTEXTO.md` é configurável — a árvore de pastas do projeto **não precisa** seguir um template rígido. Basta o `project.json` apontar corretamente.

### Registro do projeto

```json
{
  "project_id": "meu-projeto",
  "working_dir": "/caminho/para/meu/projeto",
  "agents": [
    {
      "agent_id": "dev",
      "module_path": "src/agents/worker.py",
      "class_name": "DeclarativeWorker",
      "context_file": "agentes/dev/CONTEXTO.md",
      "llm_provider": "auto"
    }
  ]
}
```

Arquivo de referencia: [`contexts/demo-onboarding/project.json`](../contexts/demo-onboarding/project.json).

### Código Python (opcional)

Agentes podem ser:

1. **Puramente declarativos** — `DeclarativeWorker` + JSON/YAML + `CONTEXTO.md`
2. **Classes no projeto** — referenciadas via `AgentReference` (`module_path` + `class_name`)

Em ambos os casos, o **domínio** pertence ao projeto; a Factory só executa.

### Dados de runtime

Gerados em `.agent-factory/` (gitignored):

- eventos, missões, logs
- árvore de contexto por agente/projeto
- estado operacional do Console AFP

---

## Modos de execução

### Standard (com RabbitMQ)

Recomendado para **múltiplos runtimes**, paralelismo real e observabilidade completa.

```
Coordinator ──RPC──► RabbitMQ ──► AgentRuntime (dev, qa, …)
                      task.run.{id}     │
                      task.result.{id}  ◄┘
```

Subir stack:

```powershell
docker compose up -d rabbitmq
.\start_afp.ps1
```

### Lite (fallback in-process)

Quando RabbitMQ **não** está disponível, o coordenador delega **no mesmo processo** ([`coordinator.py`](../src/agents/coordinator.py) — fallback após falha RPC).

| | Standard | Lite |
|---|---|---|
| RabbitMQ | Obrigatório | Opcional |
| Processos | 1 por agente + MCP + dashboard | MCP + dashboard + coordenador (workers in-process) |
| Paralelismo | Real (filas) | Sequencial / limitado |
| Uso | Produção, dogfood AFP-Team | Dev rápido, máquinas sem Docker |

**Direção de produto:** Lite como default para onboarding; Standard para operação séria. Formalização do Lite está no backlog.

---

## Fluxo de uma missão

```
1. IDE chama run_objective(project_id, objective) via MCP
2. MCP encaminha ao Coordenador
3. Coordenador carrega CONTEXTO.md + tree/ do projeto
4. LLM gera plano (DAG de tasks com depends_on)
5. Para cada task:
   a. Publica em task.run.{agent_id} (Standard)
   b. Ou delegate() in-process (Lite)
6. Worker carrega CONTEXTO.md, executa ação, retorna TaskOutput
7. Coordenador consolida, reflete, persiste em tree/
8. Resultado estruturado volta ao IDE via MCP
9. Dashboard recebe eventos SSE em tempo real
```

Erros retornam `StructuredError` — ver [AGENTS.md](../AGENTS.md#the-error-iteration-loop).

---

## Comunicação

| Canal | Protocolo | Uso |
|---|---|---|
| IDE ↔ AFP | **MCP** (SSE :8081) | `run_objective`, `run_agent` — síncrono |
| Agente ↔ Agente | **RabbitMQ** (exchange `afp`) | Delegação, RPC, progresso |
| Console AFP | **SSE + REST** (:8082) | Live Stream, Mission Control, config |
| Config CRUD | **REST** | Projetos, times, agentes, LLM |

### Routing keys (RabbitMQ)

| Key | Direção | Descrição |
|---|---|---|
| `task.run.{agent_id}` | Coordenador → Worker | Delegar tarefa |
| `task.result.{agent_id}` | Worker → Coordenador | Resultado |
| `agent.ask.{agent_id}` | Qualquer → Agente | Diálogo |
| `agent.answer.{agent_id}` | Agente → Qualquer | Resposta |

---

## LLM — SmartRouter

[`src/llm/__init__.py`](../src/llm/__init__.py) centraliza provedores:

- **Cloud free:** Groq, Gemini, OpenRouter, Cerebras, Mistral, HuggingFace, OpenCode Zen…
- **Local:** Ollama, multi-model squad
- **Auto:** tenta cloud → local → mock

Chaves em `.env` (gitignored). Cada agente pode ter `llm_provider` no `project.json` ou config JSON.

AFP **complementa** Cursor/OpenCode — não substitui. Use Cursor para codar; AFP para orquestrar times de agentes project-native.

---

## Demo vs produto

| | demo-onboarding | Produto AFP |
|---|---|---|
| Proposito | Validar setup e primeira missao | Runtime generico para qualquer org |
| Agentes | coordenador + dev (minimo) | Configuraveis pelo usuario |
| Local | `contexts/demo-onboarding/` (versionado) | `contexts/{seu-projeto}/` (local) |
| Papeis fixos | Exemplo apenas | **Nao** prescreve dev/qa como unico modelo |

Projetos de negocio ficam em `contexts/` **localmente** — nao sao commitados no repo publico. Ver [contexts/README.md](../contexts/README.md).

---

## Integração natural (visão)

Objetivo de produto: integração **quase transparente** via:

1. **MCP** — IDE descobre `run_objective` automaticamente
2. **`.agent-factory/`** no projeto — runtime, eventos, árvore
3. **Console AFP** — configurar org visualmente (Agent Card), não só perfis dev/qa
4. **Modo Lite** — subir sem Rabbit para experimentação

Roadmap detalhado: [backlog.md](backlog.md).

---

## Estrutura do repositório (plataforma)

```
agent-factory/
├── src/
│   ├── agents/          coordinator.py (built-in) + worker.py + runtime.py
│   ├── agents/configs/  defaults declarativos para DeclarativeWorker
│   ├── sdk/             AgentFactory, StandardBaseAgent
│   ├── eventbus/        AMQP / RPC
│   ├── mcp/             MCP Server
│   ├── llm/             SmartRouter
│   ├── registry.py      projetos e referências
│   └── loader.py        import dinâmico
├── contexts/            _template/ + demo-onboarding/ (projetos locais gitignored)
├── dashboard-react/     Console AFP (React)
├── docs/                documentação (este arquivo)
├── start_afp.ps1        startup Windows (Standard stack)
├── docker-compose.yml   RabbitMQ
├── AGENTS.md            guia para agentes IA
└── MEMORIA.md           memória imutável pós-compactação
```

---

## Decisões arquiteturais (ADRs resumidos)

| Decisão | Motivo |
|---|---|
| Agentes no projeto, não no Factory | Desacoplar domínio de infra; reuso entre projetos |
| Coordenador built-in | Garantir orquestração consistente; único ponto de DAG/reflexão |
| Workers declarativos | Escalar papéis sem novo `.py` por agente |
| MCP + RabbitMQ híbrido | IDE precisa sync; agentes precisam async/paralelo |
| Fallback in-process | Dev experience sem Docker; degradação graciosa |
| CONTEXTO.md + tree/ | Identidade estável + aprendizado incremental |
| SmartRouter multi-provider | Free tier + resiliência; usuário BR sem cartão |

---

## Documentos relacionados

| Documento | Conteúdo |
|---|---|
| [AGENTS.md](../AGENTS.md) | Fluxo recursivo de delegação para agentes IA |
| [MEMORIA.md](../MEMORIA.md) | Resumo imutável pós-compactação |
| [console-afp-schema.md](console-afp-schema.md) | Schema Missão, Tarefa, Agente |
| [usage-context.md](usage-context.md) | Personas e fluxos de navegação |
| [design-evaluation.md](design-evaluation.md) | Avaliação UX do Console AFP |
| [backlog.md](backlog.md) | Epics e prioridades |
| [LLM_INSTRUCOES.md](LLM_INSTRUCOES.md) | Instruções para LLMs operando a plataforma |

---

## Próximos passos arquiteturais

1. **Formalizar Modo Lite** — flag/env, startup único, documentar trade-offs
2. **Agent Card configurável** — org visual, papéis arbitrários (não só dev/qa)
3. **ARCHITECTURE ↔ README** — README enxuto apontando para este doc
4. **Integração `.agent-factory/` nos projetos** — scaffold ao registrar projeto
