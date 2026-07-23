# Backlog — Agent Factory Platform

## Prioridades (definidas pelo time de negocios)

| Prioridade | Epic | Justificativa |
|------------|------|---------------|
| 1 | E-002 | Fundacional: sem configuracao, nada funciona |
| 2 | E-001 | Diferencial principal, maior valor percebido |
| 3 | E-010 | UI Refresh: hierarquia visual, grupos colapsaveis, responsividade |
| 4 | E-003 | Experiencia integrada, depende de E-002 e E-001 |
| 5 | E-004 | Diagnostico, secundario ao monitoramento |
| 6 | E-005 | Suporte, ja em andamento |
| 7 | E-006 | Baixo valor no momento, postergavel |

## Infra-Estrutura

### Modelos LLM Locais (Ollama)
Cinco modelos rodando localmente via Ollama (GPU 6GB VRAM | RAM 40 GB):

| Modelo | Tamanho | VRAM | Tempo | Uso | Agentes |
|--------|---------|------|-------|-----|---------|
| `deepseek-r1:8b` ⭐ | 5.2 GB | 4.7 GB ✅ | ~84s | Geral, código, reasoning | Coordenador, Dev, QA |
| `dolphin3` ⚡ | 4.9 GB | 4.8 GB ✅ | ~20s | Tarefas rápidas, protótipos | — |
| `phi4` ⭐ | 9.1 GB | 4.9 GB ⚠️ | ~116s | Complexo, arquitetura, math | Arquiteto, Negócios |
| `qwen3-vl:8b` 🏆 | 6.1 GB | 5.6 GB ⚠️ | ~107s | Visão, OCR, imagens | — |
| `gemma4` | 9.6 GB | 5.0 GB ⚠️ | ~48s | Tool calling, multimodal | Designer |

**Configuração por agente:**
| Agente | Modelo | Provider |
|--------|--------|----------|
| Coordenador | DeepSeek R1 (8B) | `ollama:deepseek-r1:8b` |
| Arquiteto | Phi-4 | `ollama:phi4` |
| Designer | Gemma 4 | `ollama:gemma4` |
| Dev | DeepSeek R1 (8B) | `ollama:deepseek-r1:8b` |
| QA | DeepSeek R1 (8B) | `ollama:deepseek-r1:8b` |
| Negócios | Phi-4 | `ollama:phi4` |

> **Nota:** Modelos `deepseek-coder-v2` (8.9 GB) e `gemma3:4b` (3.3 GB) foram removidos por desempenho inferior. Ver `docs/modelos-locais-benchmark.md`. |

### E-007: Gestão de Modelos e API Keys
**Prioridade:** 5
**Status:** Implementado ✅

- **Auto-discovery Ollama**: scan local via `/api/llm/ollama-models` ✅
- **API Keys UI**: formulario add/remove via `/api/llm/api-keys` ✅
- **Teste de conectividade**: botao "Testar" via `POST /api/llm/test` ✅
- **Seletor de modelo melhorado**: modal LLM com metadados (tipo, benchmark, tarefas) ✅
- **Fallback automático**: postergado

## Epicos

### E-001: Console AFP — Live Stream (Monitoramento em Tempo Real)
**Prioridade:** 2
**Status:** Design

Implementar o Live Stream no Console AFP com:
- Agentes com "ar humanoide" e indicadores graficos de interacao
- 1 card por agente, 1 estado por vez (running/completed/failed/idle)
- Cadeia de delegacao visual (quem acionou quem)
- Missoes em andamento em destaque
- Missoes concluidas descem para Historico (compacto, expansivel)
- Detalhes sob demanda (modal/expansivel)
- Correcao do bug de cards duplicados (Live vs Log)

### E-002: Console AFP — Configuracao de Projetos, Times e Agentes
**Prioridade:** 1
**Status:** Implementado ✅

Tela de configuracao no Console AFP com:
- Aba "Projetos": lista projetos, edita metadados (project_id, name, team, working_dir, description) ✅
- Aba "Agentes": seleciona projeto + agente, visualiza metadados, configura LLM provider/model ✅
- Aba "LLM Providers": configuracao rapida de provider por agente com dropdown (auto/local_multi/cloud/groq/ollama/opencode_zen) ✅
- Preview de agentes com emoji, role e metadados ✅
- Integrado ao sistema de navegacao existente (botao ⚙️ no header) ✅
- Usa endpoints REST existentes (/api/agent-config POST, /api/projects GET) ✅
- Consistencia visual com o dashboard (glass morphism, neon accents, dark theme) ✅

### E-008: Remover Interaction Flow, manter apenas Mission Control
**Prioridade:** 4
**Status:** Implementado ✅

Remocao completa: funcao `renderTimeline()`, div `.timeline-panel`, CSS exclusivo.
Mission Control permanece como unica interface de visualizacao de missoes.

### E-009: Isolamento de estado entre projetos
**Prioridade:** 4
**Status:** Implementado ✅

Corrigida poluicao de estado entre projetos no dashboard:
- `state.agentsState` agora usa chave `projectId:agentId` via helper `agentKey()`
- Cache-Control adicionado ao HTML server response
- Bugs: `info` → `statusInfo` em template, `agentKeyStr` TDZ corrigido

### E-003: Console AFP — Home e Navegacao
**Prioridade:** 3
**Status:** Design

- Home com visao geral do AFP
- Mini sumarios dos projetos (clicaveis → pagina de detalhe)
- Navegacao entre telas (Home, Projetos, Configuracao, Live Stream, Log)
- Consistencia visual entre todas as telas

### E-004: Console AFP — Log e Debug
**Prioridade:** 4
**Status:** Design

Tela de Log separada do Live Stream com:
- Tabela: Timestamp | Agente | Status | Tarefa | Mensagem
- Filtros por agente, tipo, periodo
- Busca textual
- Exportacao (opcional)

### E-005: Documentacao e Schema Canonico
**Prioridade:** Medium
**Status:** Em Andamento

- `docs/console-afp-schema.md` — Schema canonico dos conceitos ✅
- `docs/console-afp-requisitos.md` — Requisitos detalhados ✅
- Contextos de negocios e designer atualizados ✅
- AGENTS.md atualizado com novos conceitos ✅

### E-006: CLI Tooling
**Prioridade:** Low
**Status:** Backlog

Interface de linha de comando para gerenciar projetos, iniciar
runtimes, e enviar objetivos sem depender do MCP ou Console AFP.

### E-011: System Tray Icon para AFP (Windows)
**Prioridade:** 2
**Status:** Backlog

Icone na bandeja do sistema (ao lado do relogio) para controlar o AFP:

**Funcionalidades:**
- Icone do AFP na system tray (area de notificacao do Windows)
- Menu de contexto com: Iniciar, Parar, Reiniciar, Abrir Dashboard
- Indicador visual de status: rodando (verde), parado (vermelho), ocupado (amarelo)
- Tooltip com info basica: PID, uptime, agentes ativos
- Iniciar automaticamente com o Windows (opcional)

**Tecnologia sugerida:** `pystray` + `PIL` (gerar icone via codigo, sem依赖 de .ico externo) ou `tkinter` nativo.

**Dependencias:**
- Usar `start_afp.ps1` como backend (start/stop ja implementados)
- Ler `.agent-factory/afp.pid` para status
- Ler eventos em `.agent-events/AFP-Team/events.jsonl` para indicador de atividade

### E-010: Console AFP — UI Refresh (Hierarquia, Grupos, Responsividade)
**Prioridade:** 3
**Status:** Parcial (A e E executados, 6 bloqueados por bug RPC)

Refresh de UI baseado na Design Evaluation (`docs/design-evaluation.md`):

| Item | Descricao | Agente |
|------|-----------|--------|
| A | Borda lateral colorida por status no card do agente | designer |
| B | Grupos colapsaveis (coord/upstream/downstream) no Team Detail | designer |
| C | Timer condicional (so aparece quando RUNNING) | designer |
| D | Config reorganizada em abas (Provedores / API Keys / Ollama) | designer+dev |
| E | Breadcrumb navegaveis em todos os niveis | dev |
| F | Modal LLM com header contextual (nome do agente + projeto) | designer |
| G | Responsividade (3/2/1 colunas conforme viewport) | dev |
| H | Logs Panel integrado ao card do agente (visual) | designer+dev |

**Dependencias:**
- B depende de A (borda de status define a identidade visual)
- D depende de E (navegacao breadcrumb para voltar)
- H depende de G (responsividade do layout)

---

## Bugs Conhecidos

| Bug | Impacto | Afeta |
|-----|---------|-------|
| RPC reply nao retorna ao coordinator | Tasks dependentes de E-010 bloqueadas | coordinator, runtime |
| Reflexao falha ao salvar arvore de contexto | Coordinator termina com warning nao critico | coordinator |
| Agente aparece como "worker" nos eventos | Dificulta identificar qual runtime executou | dashboard, events |
| SSE/Mission Control nao consome eventos do RabbitMQ | Monitor nao reflete em tempo real | dashboard |

## Issues Abertas no GitHub

- (todas fechadas — proximas issues serao criadas a partir dos epicos acima)
