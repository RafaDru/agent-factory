# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

**Agent Factory Platform (AFP)** — Python orchestration runtime. A Coordinator plans objectives via LLM and delegates to workers. Agent identity lives in `contexts/{project}/`, not in platform code.

**Public repo ships only:** `contexts/_template/` + `contexts/demo-onboarding/` (`project_id=demo-onboarding`).

Language: docs and commits are mostly **Portuguese**.

## Start here (AI operation)

1. Read `docs/AI_ONBOARDING.md` and `AGENTS.md`
2. Run `.\scripts\first-mission.ps1` (stack + smoke mission)
3. MCP SSE: `http://127.0.0.1:8081/sse` after stack is up
4. Primary tool: `run_objective(project_id="demo-onboarding", objective, context)`

**Never** run AFP servers in foreground of an interactive session — use `.\start_afp.ps1` (detached).

## Commands

```powershell
pip install -e ".[llm,dev]"
docker compose up -d rabbitmq
.\start_afp.ps1 -Restart
.\start_afp.ps1 -HealthCheck
.\scripts\first-mission.ps1
python -m pytest tests/ -q
```

React dashboard (optional): `cd dashboard-react && npm run dev` → `:5173`

## Architecture (short)

| Layer | Path |
|-------|------|
| Registry / loader | `src/registry.py`, `src/loader.py` |
| Agents | `src/agents/coordinator.py`, `worker.py`, `runtime.py` |
| MCP | `src/mcp/server.py` — `run_objective`, `list_projects`, … |
| Event bus | `src/eventbus/amqp.py` (RabbitMQ) |
| Dashboard API | `src/dashboard/server.py` — `:8080` |

Missions persist under `.agent-factory/missions/` (gitignored).

## MCP config

- Cursor: `.cursor/mcp.json` (included)
- OpenCode: `.opencode/opencode.json` → `mcp.agent-factory.url`
- Reference: `mcp.config.example.json`

## Tests

Maintained suite: `tests/` only. Root `test_*.py` / `run_*.py` are ad-hoc scripts.

## API keys

Copy `.env.example` → `.env`. At minimum one LLM provider (e.g. `GROQ_API_KEY`).
