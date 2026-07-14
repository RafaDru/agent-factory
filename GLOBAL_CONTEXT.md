# GLOBAL_CONTEXT — Agent Factory Platform (AFP)

## Proposito
AFP é uma plataforma de orquestração multiagente onde um Coordenador recebe objetivos, planeja e delega tarefas para agentes especializados (Dev, QA, Designer). Cada agente possui seu próprio LLM provider para execução autônoma.

## Agentes do Projeto

| Agente | ID | Especialidade |
|--------|----|--------------|
| Coordenador | `coordenador` | Planejamento, delegação, auditoria de qualidade |
| Dev | `dev` | Implementação de código, arquivos, scripts, git |
| QA | `qa` | Testes, lint, revisão de código, validação |
| Designer | `designer` | Pesquisa de design systems, protótipos, análise UX |

## Estrutura de Diretórios
- `src/` — Código fonte da plataforma (Python)
- `src/agents/` — Implementações dos agentes
- `src/sdk/` — SDK base para agentes
- `src/mcp/` — Servidor MCP (Model Context Protocol)
- `dashboard-react/` — Dashboard frontend (React + Elastic UI)
- `contexts/<project_id>/<agent_id>/` — Contextos individuais dos agentes
- `tests/` — Testes automatizados
- `.agent-factory/` — Dados de execução (eventos, projetos, missões)

## Estrutura de Missões
Missões ficam em `.agent-factory/missions/<mission_id>/`:
- `input/Mission_Context.md` — Contexto curado da missão
- `input/tasks/<task_id>/<agent_id>/Task_Context.md` — Contexto específico da tarefa
- `output/tasks/<task_id>/<agent_id>/result.md` — Resultado da execução
- `output/tasks/<task_id>/<agent_id>/artifacts/` — Artefatos gerados

## Convenções
- Código em Python 3.11+, React 19 + Vite para frontend
- Commits em português, descritivos
- Testes com pytest
- LLM providers: Groq (cloud, llama-3.3-70b) e Ollama (local, Mistral 7B)
- SmartRouterProvider tenta Groq primeiro, fallback para Ollama

## Working Directory
`C:/Users/rafae/agent-factory`
