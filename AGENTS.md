# Agent Factory Platform — Architecture for AI Agents

## What is this document?

This file describes how AI agents (OpenCode, Claude Code, Cursor, etc.) interact with the **Agent Factory Platform (AFP)**. If you are an AI agent reading this, your goal is to understand the recursive delegation flow so you can operate AFP autonomously.

## 🧠 Memoria Imutavel (leia apos compactacao)

Se voce perceber que perdeu contexto sobre conceitos da plataforma,
releia `MEMORIA.md` para restaurar as definicoes essenciais:
Console AFP, Live Stream vs Log, arquitetura de agentes, e regras criticas.

## ⚠️ Regra Critica: AFP deve rodar em background

**Sempre** iniciar o AFP em processo detached/background (`Start-Process` no Windows, `&` ou `nohup` no Linux). **Nunca** bloquear a sessao do chat com o servidor rodando em foreground.

Ciclo correto:
1. `Start-Process` → AFP sobe em background (PID visivel no log)
2. Sessao do chat continua livre para interagir
3. Para interagir com AFP, usar MCP client (SSE) ou HTTP (dashboard)
4. Ao finalizar: `Stop-Process` do PID do AFP

Razao: se o AFP travar a sessao, o assistente (OpenCode/Claude) nao consegue mais responder — e o usuario perde o controle do chat.

---

## Architecture Overview

```
Human User
  │
  ▼ (text prompt)
OpenCode / AI Coding Agent (session A)
  │
  │  Reads AGENTS.md → discovers MCP endpoint
  │
  ▼ (MCP tool: run_objective)
Agent Factory Platform (MCP Server)
  │
  ├── Coordinator Agent (session B)
  │     │
  │     │  Loads contexts/<project>/coordenador/CONTEXTO.md
  │     │  Plans via LLM (Groq/Ollama) or uses MCP sub-session
  │     │
  │     ├── delegate → dev (session C)
  │     │     │
  │     │     │  Loads contexts/<project>/dev/CONTEXTO.md
  │     │     │  Operates: write_file, run_git, run_tests, etc.
  │     │     │  Reports result or StructuredError
  │     │     │
  │     │     └── (may spawn sub-session for complex tasks)
  │     │
  │     ├── delegate → qa (session D)
  │     │     │
  │     │     │  Loads contexts/<project>/qa/CONTEXTO.md
  │     │     │  Operates: run_tests, lint, type_check
  │     │     │  Reports result or StructuredError
  │     │
  │     └── collects all results → reports to session A
  │
  ▼ (structured result)
Human User ← OpenCode
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Session** | A full AI agent invocation (e.g., one OpenCode conversation). Each agent gets its own session with isolated context. |
| **MCP Server** | Exposes AFP agents as tools + resources for any LLM to consume. The bridge between "parent" and "child" sessions. |
| **Coordinator** | Receives high-level objectives, generates plans, delegates to workers. The "brain" of a project. |
| **Worker** | Executes specific tasks (file ops, tests, lint, research). Each worker has its own context file and toolset. |
| **Context File** | `contexts/<project_id>/<agent_id>/CONTEXTO.md` — defines the agent's purpose, actions, examples. Incrementable over time. |
| **StructuredError** | When an agent fails, it returns `error_type`, `available_actions`, `doc_path`, and `hint`. Enables the delegator to retry with correct action. |

---

## The Recursive Delegation Flow

### Step 1: User prompts OpenCode

```
User: "Adicionar logging nos agents do Agent Factory"
OpenCode: reads AGENTS.md → discovers MCP tools → calls run_objective()
```

### Step 2: OpenCode calls AFP via MCP

```
Tool:  run_objective
Args:  project_id = "AFP-Team"
       objective = "Adicionar logging estruturado com módulo logging em todos os agentes em src/agents/"
       context = "Usar logging.basicConfig, log para arquivo em .agent-factory/logs/"
```

### Step 3: Coordinator receives objective

The Coordinator:
1. Loads its context file
2. Calls its LLM (or MCP sub-session) to generate a plan
3. Produces a DAG of tasks with dependencies
4. Delegates to workers

```json
{
  "plan": [
    {"id": "read-src", "agent": "dev", "task": {"action": "read_file", "file_path": "src/agents/base.py"}},
    {"id": "add-logging", "agent": "dev", "task": {"action": "edit_file", ...}, "depends_on": ["read-src"]},
    {"id": "run-tests", "agent": "qa", "task": {"action": "run_tests", "path": "tests/"}, "depends_on": ["add-logging"]},
    {"id": "lint", "agent": "qa", "task": {"action": "lint", "path": "src/"}, "depends_on": ["add-logging"]},
    {"id": "commit", "agent": "dev", "task": {"action": "run_git", "args": ["commit", "-m", "..."]}, "depends_on": ["run-tests", "lint"]}
  ]
}
```

### Step 4: Each worker executes independently

Each worker receives its task, loads its context, and executes. If a worker fails, it returns a `StructuredError`. The coordinator (or parent session) can interpret the error and retry with a corrected action.

```
Worker receives:
  {"action": "edit_file", "file_path": "src/agents/base.py", "old_string": "...", "new_string": "..."}

Worker executes via subprocess:
  - Reads the file
  - Applies the change
  - Reports: {"status": "completed", "output": {"changes": 1}}
```

### Step 5: Results propagate up

```
Worker → Coordinator → MCP Server → OpenCode → User
```

Each level enriches the result with its own context. The final response to the user includes:
- What was done
- What changed (diff)
- Test results
- Lint results
- Commit hash (if git was used)

---

## The Two "Modes" of Agent Execution

### Mode A: MCP Tool Call (LLM delegating to LLM)

The parent session calls `run_agent` or `run_objective` via MCP. The AFP server executes synchronously and returns structured results. The parent LLM interprets the result and decides next steps.

```
OpenCode ──MCP──► AFP Server ──► Coordinator ──► Workers
                    │
                    ◄── results ──
```

**Used when:** Parent LLM is actively orchestrating (default).

### Mode B: Autonomous Session (agent as mini-OpenCode)

The coordinator spawns a **new AI session** (subprocess or API call to an LLM provider) with:
- Its context file as system prompt
- The objective as user prompt
- Its toolset (MCP tools or Python subprocess actions)

This session runs independently, persists its context, and reports back.

```
Coordinator ──► LLM API (Groq/Ollama) ──► sub-session
                  │
                  └── uses tools: read_file, write_file, run_git
                  │
                  ◄── result ──
```

**Used when:** Long-running tasks, or when the task is well-defined enough for an LLM to execute autonomously without parent supervision.

---

## Hybrid Communication: MCP + Event Bus (RabbitMQ)

The Agent Factory uses a **hybrid communication model**:

```
Chat IDE (OpenCode, Claude, Cursor)
  │
  ▼ MCP (sincrono, request-response)
AFP MCP Gateway (src/server/)
  │
  ├──► Session Manager
  │      │
  │      ▼ RabbitMQ (exchange: afp, topic)
  │
  ├──► Agent Runtimes (src/agents/runtime.py)
  │      │
  │      ├── dev-runtime  ── escuta: task.run.dev
  │      ├── qa-runtime   ── escuta: task.run.qa
  │      ├── designer-runtime ── escuta: task.run.designer
  │      ├── arquiteto-runtime ── escuta: task.run.arquiteto
  │      └── negocios-runtime ── escuta: task.run.negocios
  │
  └──► Dashboard (SSE + REST)
```

### Routing Keys

| Routing Key | Direction | Description |
|-------------|-----------|-------------|
| `task.run.{agent_id}` | Coordinator → Worker | Delegar tarefa para execucao |
| `task.result.{agent_id}` | Worker → Coordinator | Resultado da execucao |
| `agent.ask.{agent_id}` | Any → Agent | Pergunta/dialogo |
| `agent.answer.{agent_id}` | Agent → Any | Resposta |
| `agent.reply.{corr_id}` | Any → Any | Reply RPC (fila exclusiva) |

### Vantagens do Modelo Hibrido

| Camada | Protocolo | Quando usar |
|--------|-----------|-------------|
| **Externa** (IDE ↔ AFP) | MCP | Chamadas sincronas de ferramentas |
| **Interna** (Agente ↔ Agente) | RabbitMQ | Delegacao, dialogo, progresso parcial |
| **Monitoramento** (Console AFP) | SSE + REST | Live Stream em tempo real, historico, log |
| **Configuracao** (Console AFP) | REST | CRUD de Projetos, Times e Agentes |

### Como Executar

```bash
# 1. Iniciar RabbitMQ
docker compose up -d rabbitmq

# 2. Iniciar servidores (MCP + Dashboard)
python -m src.server.main     # MCP em background
python -m src.dashboard.server  # Dashboard em background

# 3. Iniciar runtimes dos agentes
python -m src.agents.runtime src.agents.worker.DeclarativeWorker dev AFP-Team
python -m src.agents.runtime src.agents.worker.DeclarativeWorker qa AFP-Team
python -m src.agents.runtime src.agents.worker.DeclarativeWorker designer AFP-Team

# Ou usar o script completo:
.\start_all.ps1
```

---

## MCP Server Interface

The MCP server exposes:

### Tools

| Tool | Description |
|------|-------------|
| `list_projects` | List registered projects and their agents |
| `run_objective` | Submit high-level objective to a project's coordinator |
| `run_agent` | Execute a specific agent with a task |
| `read_events` | Read recent events for monitoring |

### Resources

| URI | Content |
|-----|---------|
| `afp://{project}/context/{agent_id}` | Agent's context file |
| `afp://{project}/events` | Recent events |
| `afp://{project}/agents` | Agent references |

---

## Context Files

Each agent has a context file at `contexts/<project_id>/<agent_id>/CONTEXTO.md`.

**Purpose:** Define the agent's identity, available actions, examples, and any evolving knowledge. Context files are versioned (git) and incrementable — as the agent learns or as the user adds new capabilities, the context file grows.

**Format:**

```markdown
# <Agent ID> — <Project Name>

## Proposito
One paragraph describing the agent's role.

## Acoes Disponiveis
| Acao | Descricao |
|------|-----------|
| action_name | Description of what it does |

## Exemplos
```json
{"action": "action_name", "param": "value"}
```

## Working Directory
`/path/to/project`
```

---

## The Error Iteration Loop

When a task fails, the agent returns a `StructuredError`:

```json
{
  "error_type": "file_not_found",
  "action_requested": "edit_file",
  "available_actions": ["read_file", "list_directory", "write_file"],
  "doc_path": "src/agents/base.py",
  "hint": "O arquivo especificado nao existe. Use list_directory para descobrir arquivos disponiveis."
}
```

The delegating agent (or parent LLM) should:
1. Read `error_type` and `hint`
2. Choose a different action from `available_actions`
3. Retry with corrected parameters
4. Repeat until success or fatal error

---

## Project Types

### AFP-Team (Agent Factory Platform Team)
**Purpose:** A equipe de agentes que evolui a própria Agent Factory Platform de forma recursiva. Este é o projeto meta, onde a plataforma constrói a si mesma.
**Agents:** `coordenador` (orquestrador), `dev` (desenvolvimento), `qa` (qualidade), `designer` (UX/UI). Cada agente possui seu próprio LLM provider para raciocínio autônomo.

### pta
**Purpose:** Build and evolve the Personal Trainer App with AI and computer vision.
**Agents:** coordenador, frontend-mobile, visao-computacional, ui-ux, qa, renderizacao, research, code-executor

### cr10se
**Purpose:** Optimizar e monitorar a impressora 3D Creality CR-10 SE com Klipper.
**Agentes:** coordenador (orchestrator), klipper (comunicacao SSH/WS), pipeline (STL->GCode->print), visao (monitoramento OpenCV), resume (retomada de impressao), qa (qualidade/diagnostico)
**Working Directory:** `C:\Users\rafae\Documents\Impressao 3D`

**Contexto:** CR-10 SE (F003), Klipper v1.1.0.28, IP 192.168.18.200, SSH root/Creality2023.
**Parametros:** max_velocity 200, max_accel 2000, PA 0.030, 210°C bico / 65°C mesa, Flow 115%, Speed 50%.

---



## Implementation Roadmap

| Step | What | Status |
|------|------|--------|
| 1 | Document architecture (this file) | ✅ Done |
| 2 | MCP server exposing agents as tools | ✅ Done |
| 3 | Coordinator with LLM brain (plan generation) | ✅ Done |
| 4 | All agents with native LLM provider | ✅ Done |
| 5 | Spawn sub-session mechanism (worker as mini-LLM) | ⏳ Planned |
| 6 | Update all context files with new flow | ✅ Done |
| 7 | Recursive self-improvement via AFP-Team | 🎯 Goal |
| 8 | Console AFP — Live Stream, Configuracao, Log | 📋 Planned |

---

## Documentos de Referencia

| Documento | Conteudo |
|-----------|----------|
| `MEMORIA.md` | **Memoria imutavel** — releia apos compactacao para restaurar conceitos essenciais |
| `docs/console-afp-schema.md` | Schema canonico dos conceitos (Missao, Tarefa, Delegacao, Live Stream, Log) |
| `docs/console-afp-requisitos.md` | Requisitos detalhados do Console AFP |
| `docs/backlog.md` | Backlog operacional do projeto AFP-Team |

