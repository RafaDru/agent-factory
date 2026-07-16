# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Agent Factory Platform (AFP) is a Python multi-agent orchestration framework. A **Coordinator** agent receives an objective, plans it via an LLM, and delegates tasks to specialized **worker** agents (dev, qa, designer, etc.). Projects are fully segregated: the factory is an execution platform that *references and loads* agents on demand — the agents themselves live in per-project context files, not in the platform.

Language note: most docs, comments, and commit messages are in **Portuguese**. Match that convention when committing.

## Commands

Python 3.11+ required. Run everything from the repo root (`C:/Users/rafae/agent-factory`).

```bash
pip install -e .              # core (langgraph, pydantic)
pip install -e .[llm]         # + Groq/Ollama providers
pip install -e .[dev]         # + pytest, pytest-cov
```

**Tests** (`pyproject.toml` sets `testpaths = ["tests"]`, verbose by default):
```bash
pytest                                          # the maintained suite in tests/
pytest tests/test_context_manager.py            # one file
pytest tests/test_loader.py::test_name          # one test
```
Note: many `test_*.py` files at the repo root are ad-hoc/experimental scripts, **not** part of the `tests/` suite. Prefer `tests/` for the real suite.

**Server lifecycle** — use `server_ctl.py`, which tracks PIDs in `.agent-factory/.server_pids.json`:
```bash
python server_ctl.py start|stop|restart|status
python start_agent_factory.py [--demo] [--no-ollama] [--port 9090]   # full startup (manages Ollama GPU env + dashboard)
```

**React dashboard** (`dashboard-react/`, React 19 + Vite + Elastic EUI):
```bash
cd dashboard-react
npm run dev      # Vite dev server
npm run build    # production build
npm run lint     # oxlint
```

**MCP server** (`src/mcp/server.py`): `run_stdio()` for stdio transport, `run_sse(port=8081)` for SSE.

## ⚠️ Critical operational rule

**Never run AFP/servers in the foreground of an interactive session.** Always start detached (`Start-Process` on Windows, `&`/`nohup` on Linux) or via `server_ctl.py start`. A foreground server blocks the session and the user loses control of the chat. Interact with a running AFP through the MCP client (SSE) or HTTP (dashboard).

## Architecture

The system has three layers that meet at the **registry**:

- **`src/registry.py` + `src/loader.py`** — `ProjectRegistry` holds `ProjectConfig`s and *references* to agents (`AgentReference`), not instances. `AgentLoader` instantiates agents on demand. This is the segregation boundary: agents are loaded per project, per request. Start here to understand how anything gets executed.

- **Agents (`src/agents/`)** — `base.py` defines `AgentBase`, `ContextManager` (tracks tokens/KB per agent, auto-compresses at >80%), and the `Coordinator`. `real.py` has `SubprocessAgent` (runs code/file ops via subprocess), `LLMAgent`, `ReviewerAgent`. Project-specific agents (e.g. `cr10se_*`, `coordinator.py`, `qa.py`, `design_factory.py`) build on these.

- **Orchestration (`src/orchestrator/`)** — LangGraph-based `graph.py`/`pipeline.py` build a DAG of tasks with `depends_on` dependencies; `context_injector.py` and `cache.py` manage context. A worker that fails returns a **`StructuredError`** (`error_type`, `available_actions`, `doc_path`, `hint`) so the delegator can pick a valid action and retry — this error-iteration loop is central to how delegation recovers.

Supporting pieces:
- **`src/protocols/`** — `schema.py` (Pydantic models: `ProjectConfig`, `AgentEvent`, `AgentStatus`), `events.py` (`EventNotifier` writes JSONL to `.agent-factory/` and streams SSE to dashboards), `tasks.py` (task lifecycle).
- **`src/llm/`** — pluggable providers. `get_provider("auto")` tries cloud → local → mock; `SmartRouterProvider` tries Groq then falls back to Ollama. ~12 providers supported (Groq, Gemini, DeepSeek, Cerebras, Mistral, etc.); API keys load from root `.env` automatically (see `.env.example`).
- **`src/mcp/server.py`** — exposes agents as MCP tools (`run_objective`, `run_agent`, `list_projects`, `register_project`, `add_agent`, `read_events`, `figma_get_file`) and resources (`afp://{project}/...`). This is how external AI coding agents (OpenCode/Claude/Cursor) drive AFP.
- **`src/sdk/`** — base building blocks (`context_tree.py`, `decision.py`, `hooks.py`, `factory.py`) for authoring agents.

### Two dashboards

There are **two** dashboard implementations — don't confuse them:
1. **Legacy Python-served** — `src/dashboard/server.py` (a `ThreadingHTTPServer`) serving `src/dashboard/index.html` on port 8080. API routes live in `do_GET`/`do_POST` (`/api/events`, `/api/status`, `/api/context/stats`, `/api/agent/{id}/provider`, etc.). Much recent work edits `src/dashboard/index.html` directly.
2. **React** — `dashboard-react/` (Vite). Consumes the same JSON API.

### Contexts and missions (runtime data)

- **Context files**: `contexts/<project_id>/<agent_id>/CONTEXTO.md` — each agent's identity, available actions, and evolving knowledge (git-versioned, incrementable).
- **Missions**: `.agent-factory/missions/<mission_id>/` with `input/Mission_Context.md`, per-task `Task_Context.md`, and `output/.../result.md` + `artifacts/`.
- **`.agent-factory/`** and `.agent-events/` hold all runtime state (events, PIDs, missions) and are gitignored.

### Root-level driver scripts

`missao_*.py` and `run_*.py` at the repo root are one-off orchestration drivers: they load the registry, wire a coordinator to its subordinates, and hand it a hard-coded objective string (see `missao_redesign.py` for the pattern). They're historical/experimental — useful as examples of the API, not a stable interface.

## Registered projects

`AFP-Team` (the meta-project that evolves AFP itself: `coordenador`, `dev`, `qa`, `designer`), `pta` (Personal Trainer App), `cr10se` (Creality CR-10 SE 3D printer control), and the Solar monitor project. Each project's agents and working directory are defined via the registry / `register_project`.
