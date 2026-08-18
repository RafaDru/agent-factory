# Quick Start — Agent Factory Platform

Guia unico para subir a AFP do zero e rodar a primeira missao.
Testado em **Windows** com Python 3.11+.

> Beta tecnico — setup manual. Projetos de negocio ficam locais em `contexts/`.

---

## Pre-requisitos

| Requisito | Versao | Verificar |
|-----------|--------|-----------|
| Python | 3.11+ | `python --version` |
| Docker Desktop | recente | `docker compose version` |
| Git | qualquer | `git --version` |
| Chave LLM | Groq ou OpenCode Zen | copie `.env.example` → `.env` |

Opcional: Node.js 20+ (Console React em `:5173`).

---

## 1. Clone e dependencias

```powershell
git clone https://github.com/RafaDru/agent-factory.git
cd agent-factory

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[llm,dev]"

copy .env.example .env
# Edite .env e preencha pelo menos GROQ_API_KEY (ou use OpenCode Zen)
```

---

## 2. Event bus (RabbitMQ)

```powershell
docker compose up -d rabbitmq
```

Sem Docker: a AFP usa fallback in-process (Modo Lite). Missoes simples funcionam;
delegacao multi-runtime fica limitada.

---

## 3. Subir a stack

```powershell
.\start_afp.ps1 -Restart
.\start_afp.ps1 -HealthCheck
```

Processos esperados: dashboard `:8080`, MCP `:8081`, coordenador + dev
(projeto padrao `demo-onboarding`).

| Servico | URL |
|---------|-----|
| Dashboard API | http://localhost:8080 |
| MCP (SSE) | http://127.0.0.1:8081/sse |
| RabbitMQ UI | http://localhost:15672 (afp / afp123) |

Console React (opcional):

```powershell
cd dashboard-react
npm install
npm run dev
# http://localhost:5173
```

---

## 4. Verificar APIs

```powershell
# Projetos descobertos
curl http://localhost:8080/api/projects

# Health implicito
curl http://localhost:8080/api/missions
```

Deve listar `demo-onboarding`.

---

## 5. Primeira missao (smoke)

Com a stack no ar:

```powershell
python run_smoke_e012.py
```

Objetivo: coordenador delega `read_file` em `docs/backlog.md` via RPC.
Saida esperada: `SMOKE_OK` em ~30s.

Alternativa via MCP (Cursor / OpenCode): configure MCP em
`http://127.0.0.1:8081/sse` e chame `run_objective` com
`project_id=demo-onboarding`. Ver [AGENTS.md](../AGENTS.md).

---

## 6. Registrar seu projeto

O repo publico traz apenas `_template/` e `demo-onboarding/`.
Seus projetos ficam locais (gitignored):

```powershell
.\scripts\scaffold_project.ps1 -ProjectId "meu-projeto" -ProjectName "Meu Projeto"
.\start_afp.ps1 -Restart -ProjectId "meu-projeto"
```

Guia completo: [playbook-onboarding.md](playbook-onboarding.md)

---

## Troubleshooting

| Sintoma | Acao |
|---------|------|
| Healthcheck FAIL | `.\start_afp.ps1 -Repair` |
| Porta 8080 ocupada | `.\start_afp.ps1 -Stop` e libere a porta |
| RPC timeout | confirme RabbitMQ: `docker compose ps` |
| LLM sem resposta | verifique `.env` e provider em `project.json` |
| Missao inventa acao | use acoes de `get_capabilities`; ver backlog E-012-K |

Logs: `.agent-factory/logs/`

---

## Proximos passos

- [ARCHITECTURE.md](ARCHITECTURE.md) — como a plataforma funciona
- [contexts/README.md](../contexts/README.md) — o que versionar vs. local
- [backlog.md](backlog.md) — roadmap
