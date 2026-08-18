# Backlog — Agent Factory Platform

> **Atualizado:** 27/07/2026 — foco em operação estável e replicação.

## Prioridades (definidas pelo time de negocios)

| Prioridade | Epic | Justificativa |
|------------|------|---------------|
| 1 | **E-012** | Confiabilidade: sem RPC/SSE estáveis, agentes não operam |
| 2 | **E-013** | Onboarding/replicação: levar AFP a outros projetos |
| 3 | E-010 | UI Refresh (desbloqueado após E-012) |
| 4 | E-003 | Home e navegação integrada |
| 5 | E-004 | Log e debug dedicado |
| 6 | E-006 | CLI tooling |
| 7 | E-015 | Spawn sub-session (worker autônomo) |

### Concluídos (base operacional)

| Epic | Status |
|------|--------|
| E-002 Configuração (projetos, agentes, LLM) | ✅ |
| E-001 Mission Control (Global + Local) | ✅ |
| E-007 Gestão de modelos e API keys | ✅ |
| E-008 Remover Interaction Flow | ✅ |
| E-009 Isolamento entre projetos | ✅ |
| E-011 System Tray (Windows) | ✅ |
| E-005 Documentação e schema canônico | ✅ (contínuo) |
| E-014 Ciclo de vida de missão (`status.json`) | ✅ parcial |

---

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

**Configuração por agente:** ver `docs/modelos-locais-benchmark.md`.

---

## Epicos — Plataforma (operação e replicação)

### E-012: Confiabilidade da Plataforma
**Prioridade:** 1
**Status:** Em andamento (fixes 27/07 aplicados)

Garantir que missões autônomas completem de ponta a ponta.

| Item | Descricao | Status |
|------|-----------|--------|
| A | Runtimes usam notifier canônico (`.agent-factory/events/`) | ✅ |
| B | RPCClient: correlation_id por chamada, poll seguro | ✅ |
| C | Coordinator: parsing TaskResult do runtime | ✅ |
| D | Bridge SSE ← RabbitMQ (`event.broadcast.#`) | ✅ |
| E | Reflexão: persistência tree tolerante a falhas | ✅ |
| F | Testes RPC parsing | ✅ |
| I | RPC: `needs_direction` não conta como success | ✅ (27/07) |
| G | Healthcheck + restart automático (tray/start_afp) | ✅ (27/07) |
| H | Coordinator retry inteligente (não repetir mesma ação) | 📋 |
| J | LLM AFP-Team → `opencode:deepseek-v4-flash` (Go) | ✅ (27/07) |
| K | Tool-calling loop (15 iter sem resposta final) | 📋 |

### E-013: Onboarding e Replicação de Projetos
**Prioridade:** 2
**Status:** Backlog

Formalizar como levar AFP a um projeto novo (PTA, CR-10 SE, Solar…).

| Item | Descricao | Status |
|------|-----------|--------|
| A | Playbook: register → `contexts/{proj}/` → primeira missão | ✅ |
| B | Template `contexts/_template/` + `scripts/scaffold_project.ps1` | ✅ (27/07) |
| C | Formalizar Modo Lite (default onboarding, sem RabbitMQ) | 📋 |
| D | Scaffold `.agent-factory/` no projeto alvo | 📋 |
| E | Agent Card — org configurável (papéis arbitrários) | 📋 |
| F | Runbook operacional (start, verify RPC, troubleshoot SSE) | 📋 |

**Exemplos versionados:** `contexts/{_template,demo-onboarding}/`

Projetos de negocio ficam locais (nao commitados). Ver [contexts/README.md](../contexts/README.md).

### E-014: Ciclo de Vida de Missão
**Prioridade:** 2
**Status:** Parcial ✅

| Item | Descricao | Status |
|------|-----------|--------|
| A | Enum `MissionStatus` + `status.json` | ✅ |
| B | API `/api/missions` expõe status | ✅ |
| C | React + tray consomem status formal | ✅ |
| D | Eventos terminais canônicos (concluida/parcial/falhou) | ✅ |
| E | `/api/missions` expõe `status` de `status.json` | ✅ (27/07) |
| F | Histórico compacto no Mission Control | 📋 |

### E-015: Spawn Sub-Session (Worker Autônomo)
**Prioridade:** 7
**Status:** Backlog

Worker como mini-sessão LLM autônoma (AGENTS.md step 5).

---

## Epicos — Console AFP (produto)

### E-001: Console AFP — Live Stream / Mission Control
**Status:** ✅ Implementado

### E-002: Console AFP — Configuração
**Status:** ✅ Implementado

### E-003: Console AFP — Home e Navegação
**Prioridade:** 4 | **Status:** Design

### E-004: Console AFP — Log e Debug
**Prioridade:** 5 | **Status:** Design

### E-005: Documentação e Schema Canônico
**Status:** ✅ Em manutenção contínua

- `docs/console-afp-schema.md`, `docs/console-afp-requisitos.md`
- `docs/opendesign-cursor.md`, `AGENTS.md`, `MEMORIA.md`

### E-006: CLI Tooling
**Prioridade:** 6 | **Status:** Backlog

### E-007: Gestão de Modelos e API Keys
**Status:** ✅ Implementado

### E-008: Remover Interaction Flow
**Status:** ✅ Implementado

### E-009: Isolamento de estado entre projetos
**Status:** ✅ Implementado

### E-010: Console AFP — UI Refresh
**Prioridade:** 3
**Status:** Parcial (A e E ✅; B–H desbloqueados após E-012)

| Item | Descricao | Agente | Status |
|------|-----------|--------|--------|
| A | Borda lateral colorida por status | designer | ✅ |
| B | Grupos colapsáveis no Team Detail | designer | 📋 |
| C | Timer condicional (só RUNNING) | designer | 📋 |
| D | Config em abas (Provedores / Keys / Ollama) | designer+dev | 📋 |
| E | Breadcrumb navegáveis | dev | ✅ |
| F | Modal LLM contextual | designer | 📋 |
| G | Responsividade 3/2/1 colunas | dev | 📋 |
| H | Logs Panel no card do agente | designer+dev | 📋 |

### E-011: System Tray Icon (Windows)
**Status:** ✅ Implementado

```powershell
.\start_afp_tray.ps1
# pythonw scripts/afp_tray.py
```

---

## Bugs Conhecidos

| Bug | Impacto | Status |
|-----|---------|--------|
| Runtimes gravavam em `.agent-events/` (dashboard lia `.agent-factory/events/`) | SSE/REST não refletiam agentes | ✅ Corrigido (E-012-A) |
| RPC reply parsing frágil / timeout curto em delegate | Missões falhavam silenciosamente | ✅ Corrigido (E-012-B/C) |
| Bridge SSE não consumia RabbitMQ | Monitor cego em tempo real | ✅ Corrigido (E-012-D) |
| Reflexão crashava ao persistir tree | Warning pós-missão | ✅ Corrigido (E-012-E) |
| `/api/missions` retornava `status=None` | Console não mostrava status canônico | ✅ Corrigido (E-014-E) |
| Missão `completed` com steps `needs_direction` | Falso positivo — artefato não criado | ✅ Corrigido (E-012-I) |
| Agente aparece como "worker" nos eventos | Identificação difícil no dashboard | 📋 |
| Servidores caem silenciosamente (`pythonw`) | Tray degradado/offline | 📋 (E-012-G) |
| Coordinator repete mesma ação no retry | Loop ineficiente | 📋 (E-012-H) |

## Issues Abertas no GitHub

- (todas fechadas — próximas issues a partir dos épicos acima)

## Fonte de verdade operacional

| Documento | Papel |
|-----------|-------|
| `docs/backlog.md` | Este arquivo — épicos e prioridades |
| `contexts/afp-team/coordenador/tree/priorizacao.md` | Espelho para o agente coordenador |
| `docs/ARCHITECTURE.md` | Princípios Standard vs Lite, separação Factory/agentes |
