# AI Onboarding — operar a AFP com assistentes

Guia para **Cursor, OpenCode, Claude Code** (e humanos pedindo ajuda a uma IA).
Leia este arquivo antes de `run_objective` ou qualquer missao.

---

## Prompt sugerido (cole no chat da IDE)

```
Leia docs/AI_ONBOARDING.md e AGENTS.md.
Execute scripts/first-mission.ps1 para validar o setup.
Se passar, use MCP run_objective com project_id=demo-onboarding para
ler docs/QUICKSTART.md e resumir os passos.
```

---

## Checklist rapido

| # | Passo | Comando |
|---|--------|---------|
| 1 | Dependencias | `pip install -e ".[llm,dev]"` |
| 2 | API key | `copy .env.example .env` e preencha `GROQ_API_KEY` (ou outro provider) |
| 3 | RabbitMQ | `docker compose up -d rabbitmq` |
| 4 | Stack AFP | `.\start_afp.ps1 -Restart` |
| 5 | Health | `.\start_afp.ps1 -HealthCheck` |
| 6 | Smoke | `.\scripts\first-mission.ps1` |

---

## MCP por IDE

### Cursor (recomendado)

O repo ja inclui `.cursor/mcp.json` apontando para SSE `:8081`.

1. Suba a stack (`start_afp.ps1`)
2. Em **Settings → MCP**, confirme o servidor `agent-factory`
3. No chat Agent, peça: *"use run_objective no demo-onboarding"*

Regra automatica: `.cursor/rules/afp-operate.mdc`

### OpenCode

Edite `.opencode/opencode.json` — bloco `mcp` com URL SSE (apos subir stack).
Ou rode MCP stdio: `python -m src.mcp.server` (sem `--sse`).

### Claude Code

Use `mcp.config.example.json` como referencia. SSE apos `start_afp.ps1`,
ou stdio com `python -m src.mcp.server` na raiz do repo.

### GitHub Copilot

Copilot **nao** expoe MCP da AFP. A IA pode:

- Rodar `.\scripts\first-mission.ps1` no terminal integrado
- Editar codigo e docs
- Nao orquestra missoes via `run_objective` nativamente

---

## Tools MCP disponiveis

| Tool | Uso |
|------|-----|
| `run_objective` | Missao completa (coordenador planeja + delega) |
| `run_agent` | Uma acao em um agente especifico |
| `list_projects` | Projetos em `contexts/` |
| `register_project` | Registrar novo projeto |
| `read_events` | Eventos recentes do dashboard |

Endpoint SSE: `http://127.0.0.1:8081/sse` (stack rodando).

---

## Projeto padrao

- **ID:** `demo-onboarding`
- **Agentes:** `coordenador`, `dev`
- **working_dir:** `.` (raiz do repo)

Exemplo `run_objective`:

```json
{
  "project_id": "demo-onboarding",
  "objective": "Ler docs/QUICKSTART.md com read_file e listar os 6 passos do checklist",
  "context": "Plano minimo: 1 step, agent dev, action read_file, file_path docs/QUICKSTART.md"
}
```

---

## Erros comuns

| Erro | Causa | Correcao |
|------|-------|----------|
| MCP connection refused | Stack parada | `.\start_afp.ps1 -Restart` |
| coordinator_not_found | Projeto errado | use `demo-onboarding` |
| RPC timeout | RabbitMQ off | `docker compose up -d rabbitmq` |
| LLM vazio / plano ruim | Sem `.env` | Preencha API key |
| Acao inventada | Tool-calling LLM | contexto com acao valida; ver E-012-K |

---

## Documentos relacionados

- [QUICKSTART.md](QUICKSTART.md) — setup humano
- [AGENTS.md](../AGENTS.md) — arquitetura MCP e delegacao
- [playbook-onboarding.md](playbook-onboarding.md) — novo projeto
