# Agent Factory Platform

**Runtime de organizacao agentica** — orquestra times de agentes de IA cujas
identidades **moram nos projetos de origem**, nao na plataforma.

> Beta — v3.0.0 · Early adopters welcome · [Quick Start](docs/QUICKSTART.md) · [Contributing](CONTRIBUTING.md)

---

## Principio central

> **Factory = execucao e comunicacao. Agentes = nos projetos.**

A AFP fornece coordenador, event bus, MCP, roteamento de LLM e Console AFP.
Cada projeto registra seus agentes via `contexts/{proj}/project.json` e
`CONTEXTO.md` — a Factory referencia e executa, sem acoplar dominio de negocio.

**Arquitetura:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Em 30 segundos

```
IDE (Cursor / OpenCode)
  │  MCP run_objective
  ▼
AFP — Coordenador → DAG → Workers
  │                      ↑ CONTEXTO.md do projeto
  ▼
Console AFP (:8080) — Mission Control em tempo real
```

| Peca | O que faz |
|------|-----------|
| **Coordenador** | Planeja, delega, consolida (codigo fixo da plataforma) |
| **Workers** | Executam tarefas — identidade vem do projeto |
| **MCP** (:8081) | Gateway para IDEs |
| **RabbitMQ** | Bus de delegacao (opcional — ha fallback in-process) |
| **SmartRouter** | Groq, OpenCode Zen, Ollama, OpenRouter… |

---

## Quick start

**Pre-requisitos:** Python 3.11+, Docker (opcional), chave LLM (ex.: Groq ou OpenCode Zen).

```powershell
# 1. Instalar dependencias
pip install -e ".[llm,dev]"

# 2. Event bus (modo Standard)
docker compose up -d rabbitmq

# 3. Subir stack AFP (projeto demo padrao)
.\start_afp.ps1

# 4. Console API
# http://localhost:8080

# 5. MCP (IDE)
# http://127.0.0.1:8081/sse
```

Sem Docker: o coordenador usa **fallback in-process** quando RabbitMQ nao
esta disponivel. Ver [docs/ARCHITECTURE.md#modos-de-execucao](docs/ARCHITECTURE.md#modos-de-execucao).

**Console React** (opcional): `cd dashboard-react && npm install && npm run dev` → `:5173`

---

## Registrar um projeto

O repositorio publico inclui apenas `_template/` e `demo-onboarding/`.
Projetos de negocio ficam **locais** (nao commitados).

```powershell
.\scripts\scaffold_project.ps1 -ProjectId "meu-projeto" -ProjectName "Meu Projeto"
```

Estrutura gerada em `contexts/meu-projeto/`:

```json
{
  "project_id": "meu-projeto",
  "working_dir": ".",
  "agents": [
    {
      "agent_id": "coordenador",
      "module_path": "src/agents/coordinator.py",
      "class_name": "AgentFactoryCoordinator"
    },
    {
      "agent_id": "dev",
      "module_path": "src/agents/worker.py",
      "class_name": "DeclarativeWorker"
    }
  ]
}
```

Edite `coordenador/CONTEXTO.md` e `dev/CONTEXTO.md` com o dominio do **seu** repositório.

Guia completo: [docs/QUICKSTART.md](docs/QUICKSTART.md)

---

## Estrutura deste repositorio

```
agent-factory/
├── src/                 # Plataforma (coordinator, MCP, bus, LLM)
├── contexts/
│   ├── _template/       # Template para novos projetos
│   └── demo-onboarding/ # Exemplo minimo versionado
├── dashboard-react/     # Console AFP (React)
├── docs/ARCHITECTURE.md # Arquitetura canonica
├── AGENTS.md            # Guia para agentes IA (MCP, delegacao)
└── start_afp.ps1        # Startup Windows (default: demo-onboarding)
```

---

## Documentacao

| Doc | Para que |
|-----|----------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | **Comece aqui** — setup e primeira missao |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura, modos, componentes |
| [docs/playbook-onboarding.md](docs/playbook-onboarding.md) | Onboarding de projeto novo |
| [contexts/README.md](contexts/README.md) | O que versionar vs. manter local |
| [AGENTS.md](AGENTS.md) | Como agentes IA operam a AFP via MCP |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como contribuir (OSS) |
| [docs/backlog.md](docs/backlog.md) | Roadmap e epics |

---

## Roadmap (resumo)

- [x] Confiabilidade operacional (E-012 — RPC, SSE, notifier)
- [ ] Onboarding e replicacao (E-013 — Lite, runbook)
- [ ] Agent Card — org configuravel visualmente
- [ ] CLI tooling (E-006)

Detalhes: [docs/backlog.md](docs/backlog.md)

---

## License

MIT
