# Agent Factory Platform

**Runtime de organização agentica** — orquestra times de agentes de IA cujas
identidades **moram nos projetos de origem**, não na plataforma.

> Beta — v3.0.0

---

## Princípio central

> **Factory = execução e comunicação. Agentes = nos projetos.**

A AFP fornece coordenador, event bus, MCP, roteamento de LLM e Console AFP.
Cada projeto registra seus agentes via `CONTEXTO.md` e configs — a Factory
referencia e executa, sem acoplar domínio de negócio.

**Leia a arquitetura completa:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Em 30 segundos

```
IDE (Cursor / OpenCode)
  │  MCP run_objective
  ▼
AFP — Coordenador → DAG → Workers
  │                      ↑ CONTEXTO.md do projeto
  ▼
Console AFP (:8082) — Mission Control em tempo real
```

| Peça | O que faz |
|---|---|
| **Coordenador** | Planeja, delega, consolida (código fixo da plataforma) |
| **Workers** | Executam tarefas — identidade vem do projeto |
| **MCP** (:8081) | Gateway para IDEs |
| **RabbitMQ** | Bus de delegação (opcional — há fallback in-process) |
| **SmartRouter** | Groq, OpenCode Zen, Ollama, OpenRouter… |

---

## Quick start

```powershell
# 1. Event bus (Standard mode)
docker compose up -d rabbitmq

# 2. Subir stack AFP
.\start_afp.ps1

# 3. Console
# http://localhost:8082

# 4. MCP (IDE)
# http://127.0.0.1:8081/sse
```

Sem Docker: o coordenador usa **fallback in-process** quando RabbitMQ não
está disponível. Ver [docs/ARCHITECTURE.md#modos-de-execução](docs/ARCHITECTURE.md#modos-de-execução).

---

## Registrar um projeto

`contexts/meu-projeto/project.json`:

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

Crie `agentes/dev/CONTEXTO.md` no **seu** repositório com propósito e ações.
A estrutura de pastas ao redor é flexível — só o path no JSON precisa bater.

---

## Estrutura deste repositório

```
agent-factory/
├── src/                 # Plataforma (coordinator, MCP, bus, LLM)
├── contexts/            # Projetos registrados (AFP-Team = dogfood)
├── dashboard-react/     # Console AFP
├── docs/ARCHITECTURE.md # ← Arquitetura canônica
├── AGENTS.md            # Guia para agentes IA (MCP, delegação)
└── start_afp.ps1        # Startup Windows
```

---

## Documentação

| Doc | Para quê |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura, modos, componentes, princípios |
| [AGENTS.md](AGENTS.md) | Como agentes IA operam a AFP via MCP |
| [MEMORIA.md](MEMORIA.md) | Memória imutável pós-compactação |
| [docs/backlog.md](docs/backlog.md) | Roadmap e epics |
| [docs/console-afp-schema.md](docs/console-afp-schema.md) | Schema Missão / Tarefa / Agente |

---

## Roadmap (resumo)

- [ ] Modo Lite como default de onboarding
- [ ] Agent Card — org configurável visualmente (papéis arbitrários)
- [ ] Integração `.agent-factory/` nos projetos
- [ ] CLI tooling

Detalhes: [docs/backlog.md](docs/backlog.md)

---

## License

MIT
