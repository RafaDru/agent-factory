# Console AFP — Requisitos

## 1. Nomenclatura

- **Console AFP** — nome definitivo do dashboard (nao mais "dashboard")
- **Live Stream** — tela de monitoramento em tempo real (antes "Interaction Flow")
- **Log** — tela de debug com tracing tabular
- **Missao** — conjunto coordenado de tarefas com titulo humanizado

---

## 2. Telas

### 2.1 Home (Visao Geral do AFP)

**Propósito:** Mostrar todos os projetos com informacoes mais relevantes.

**Elementos:**
- Mini sumario de cada projeto (card compacto)
- Nome do projeto, numero de agentes, status geral
- Ultima execucao (missao mais recente, quem, quando, status)
- Clicavel → navega para pagina de detalhe do projeto

**Regras:**
- Priorizar informacoes mais relevantes sobre o projeto
- Sem ruido visual

---

### 2.2 Configuracao (Projetos, Times, Agentes)

**Propósito:** CRUD completo de Projetos, Times e Agentes.

**Elementos:**
- Adicionar/editar/excluir Projeto
- Adicionar/editar/excluir Time
- Adicionar/editar/excluir Agente
- Para cada agente:
  - Preview formatado do CONTEXTO.md
  - Modelo padrao do LLM (provider + model)
  - Metadados completos (module_path, class_name, acoes, etc)
  - Tudo bem formatado e indentado
  - Usuario pode optar por editar o .md diretamente

**Regras:**
- Tela separada, acessivel via navegacao superior
- Confirmacao antes de exclusoes
- Validacao de dados obrigatorios

---

### 2.3 Detalhe do Projeto

**Propósito:** Visao organizada dos Times e Agentes do projeto.

**Elementos:**
- Times organizados visualmente
- Cards de agentes com:
  - Nome, papel, emoji
  - Status atual (ready/running/completed/failed)
  - Ultima tarefa executada
  - Provider LLM configurado
  - Indicador de contexto
  - Acoes disponiveis
- Link para configuracao de cada agente

**Regras:**
- Layout limpo, hierarquia clara: Projeto → Time → Agente
- Cada agente 1 card, estado unico (sem duplicacao)

---

### 2.4 Live Stream (Monitoramento em Tempo Real)

**Propósito:** Mostrar o que esta acontecendo AGORA com o time.

**Elementos:**
- Agentes distribuidos visualmente com "ar humanoide"
- Quem esta em execucao, ha quanto tempo
- Quem acionou quem (cadeia de delegacao)
- Interacoes entre agentes com indicadores graficos
- Missoes em andamento destacadas
- Missoes concluidas → descem para o Historico (compacto)

**Regras:**
- **1 card por agente, 1 estado por vez** (CRITICO)
  - running → animacao pulsante, timer
  - completed → flash verde, volta a idle automaticamente
  - failed → destaque vermelho
  - NUNCA criar segundo card ao mudar de estado
- Detalhes verbosos sob demanda (expansivel, modal)
- Uso de recursos graficos para indicar interacoes
- Missoes concluidas no Historico sao compactas
  - Titulo humanizado, duracao, status
  - Clicavel → "foto final" do Live Stream (estado final de cada agente)

---

### 2.5 Historico do Live Stream

**Propósito:** Missoes passadas em formato compacto, acessiveis sob demanda.

**Elementos:**
- Lista de missoes concluidas (ordenada por data, decrescente)
- Cada missao:
  - Titulo humanizado
  - Duracao total
  - Status final
  - Resumo do que foi feito
- Clicavel → expande para visao detalhada
- Visao detalhada = "foto final" do Live Stream naquele momento

---

### 2.6 Log (Debug / Tracing)

**Propósito:** Depuracao profunda com visao tabular de todos os eventos.

**Elementos:**
- Tabela com colunas: Timestamp | Agente | Status | Tarefa | Mensagem
- Filtros: por agente, por tipo de evento, por periodo
- Busca textual
- Exportacao (opcional)

**Regras:**
- Tela separada do Live Stream
- Foco em tracing e debug, nao em monitoramento
- Dados completos e imutaveis

---

## 3. Correcoes de Bugs (Comportamento Atual)

### 3.1 Cards duplicados (Live vs Log misturados)
- **Problema:** Cards em "running" permanecem quando o agente completa,
  criando a impressao de que ainda esta em execucao
- **Causa:** O estado anterior nao e limpo; novo card e criado em vez de
  atualizar o existente
- **Solucao:** 1 card por agente. Estado atual substitui o anterior.
  Live Stream mostra estado presente. Log mostra historico completo.

### 3.2 Ausencia de sumario executivo
- **Problema:** A timeline mostra eventos individuais sem uma visao
  humanizada do que esta acontecendo
- **Solucao:** O titulo humanizado da missao deve ser o elemento central
  do Live Stream. Eventos individuais sao detalhes expansiveis.

---

## 4. Schema Canonico

Ver `docs/console-afp-schema.md` para definicao completa dos tipos.

**Conceitos chave:**
- Missao (tem titulo humanizado) → agrupa Tarefas
- Tarefa → trabalho atomico de um agente
- Delegacao → relacao coordenador → worker
- Interacao → dialogo entre agentes
- Live Stream → estado presente
- Log → historico completo
