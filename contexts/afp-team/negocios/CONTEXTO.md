# Negocios — Agent Factory Platform Team

## Proposito
Agente de negocios do time AFP-Team. Executa em seu proprio `AgentRuntime`,
consumindo tarefas da fila `task.run.negocios` via RabbitMQ.

Responsavel por manter o backlog priorizado, definir criterios de priorizacao,
validar requisitos de negocio, e representar a perspectiva do usuario/stakeholder.

## Ambiente de Execucao

- Runtime autonomo com LLM proprio (`ollama:phi4`)
- Recebe tarefas via Event Bus (RabbitMQ) ou fallback in-process

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| read_file | Le documentos de requisitos e backlog |
| write_file | Atualiza backlog e documentos |
| analyze_requirements | Analisa requisitos e propoe priorizacao |
| suggest_improvements | Sugere melhorias de UX/negocio |
| get_capabilities | Retorna acoes disponiveis |

## Estado do Backlog (20/07/2026)

### Ja Implementados
| Epic | Descricao | Status |
|------|-----------|--------|
| E-002 | Configuracao (Projetos, Agentes, LLM Providers) | ✅ |
| E-001 | Mission Control (Live Stream + Log Details) | ✅ |
| — | URL Routing via hash (#/ routes) | ✅ |
| — | LLM Modal com benchmarks | ✅ |
| — | Navegacao sincrona (setView) | ✅ |
| — | Bugfix: troca de projeto, context_pct 15KB | ✅ |
| — | Modelos Ollama atualizados (benchmark) | ✅ |

### Proximos Epics
| # | Epic | Descricao |
|---|------|-----------|
| 3 | **E-003** | Home e Navegacao (refinamento da tela inicial) |
| 4 | **E-004** | Log e Debug (tabela com filtros dedicada) |
| 5 | **E-005** | Dashboard de projetos externos |
| 6 | **E-006** | Documentacao |
| — | **E-008** | Remover Interaction Flow, manter apenas Mission Control ✅ |
| — | **E-007** | Gestao de Modelos e API Keys (auto-discovery Ollama, API Keys UI, teste de conectividade) |
| — | **E-009** | Isolamento de estado entre projetos (corrigido) ✅ |

### Documentos de Referencia
- `docs/backlog.md` — Backlog completo com prioridades
- `docs/console-afp-requisitos.md` — Requisitos detalhados do Console AFP
- `docs/modelos-locais-benchmark.md` — Benchmark dos modelos Ollama

## Working Directory
`C:\Users\rafae\agent-factory`
