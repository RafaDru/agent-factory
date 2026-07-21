# MEMORIA — Agent Factory Platform
> Imutável. Releia este arquivo sempre que perceber perda de contexto apos compactacao.

## Console AFP
O dashboard agora se chama **Console AFP**. Telas:
1. **Home** — Visao geral do AFP com mini sumarios dos projetos
2. **Configuracao** — CRUD de Projetos, Times e Agentes (com preview do CONTEXTO.md)
3. **Detalhe do Projeto** — Times e Agentes organizados visualmente
4. **Live Stream** — Monitoramento em tempo real (antes "Interaction Flow")
5. **Historico** — Missoes concluidas (compacto, expansivel)
6. **Log** — Debug tabular (tracing completo)

## Live Stream (Regras Criticas)
- **1 card por agente, 1 estado por vez** — NUNCA duplicar cards ao mudar estado
- running → animacao + timer | completed → flash verde → idle | failed → vermelho
- Missoes em andamento em destaque, concluidas descem para Historico
- Titulo humanizado da missao e o elemento central
- Detalhes verbosos sob demanda (expansivel / modal)

## Live Stream vs Log
| Live Stream | Log |
|-------------|-----|
| O que esta ACONTECENDO AGORA | O que ACONTECEU |
| Estado atual (1 card/agente) | Historico completo (tabela) |
| Grafico, interacoes visuais | Tabular, filtros, busca |
| Tela principal do projeto | Tela separada de debug |

## Arquitetura (Resumo)
- **Coordenador**: unico agente com codigo Python proprio (`coordinator.py`)
- **Workers**: instancias de `DeclarativeWorker` com configuracoes em `configs/{id}.json`
- **Comunicacao**: RabbitMQ (`task.run.{agent_id}`), MCP (IDE ↔ AFP)
- **Contexto**: `contexts/{projeto}/{agente}/CONTEXTO.md` (identidade)
- **Aprendizado**: `contexts/{projeto}/{agente}/tree/` (persiste apos compactacao)

## Documentos de Referencia
- `docs/console-afp-schema.md` — Schema canonico completo
- `docs/console-afp-requisitos.md` — Requisitos detalhados
- `docs/backlog.md` — Backlog operacional
- `AGENTS.md` — Documentacao arquitetural completa
