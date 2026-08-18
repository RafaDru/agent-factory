# Design Evaluation — Agent Factory Platform

## Intake
Reavaliar a interface gráfica do Console AFP com base no contexto de uso real
(personas, fluxos, dados exibidos). Propor melhorias de hierarquia visual,
organização de informação e usabilidade.

## Design System Atual (Extraído do Código)

### Cores (Dark Mode)
| Token | Valor | Função |
|-------|-------|--------|
| `--cyan` / `--cyan-glow` | `#22d3ee` | Neutro, bordas, glow |
| `--purple` / `--purple-glow` | `#a855f7` | Acento secundário |
| `--green` | `#22c55e` | Sucesso, ativo |
| `--yellow` | `#eab308` | Alerta |
| `--red` | `#ef4444` | Erro, falha |
| `--orange` | `#f97316` | Running, warning |
| `--blue` | `#3b82f6` | Info |
| `--bg` | `#0a0a0f` | Fundo escuro |
| `--bg-glass` | `rgba(255,255,255,0.03)` | Superfície glass |
| `--text-primary` | `#f1f5f9` | Texto principal |
| `--text-secondary` | `#94a3b8` | Texto secundário |
| `--text-muted` | `#64748b` | Texto apagado |

### Layout
- `radius`: lg(20px), md(14px), sm(10px), xs(6px)
- Glass morphism com bordas semi-transparentes
- Grid de projetos responsiva
- Cards com hover shadow

## Avaliação por View

### 1. Projects View
**Problemas:**
- Cards de projeto são muito similares entre si (só muda nome e números)
- O badge de "⚠️ 1 agent running" no topo é fácil de ignorar
- Projetos sem running status têm o mesmo peso visual que projetos ativos
- A ação primária (ver detalhes) exige clique no card — sem call-to-action explícito

**Oportunidade:** Destacar projetos com agentes ativos visualmente, adicionar mini-gráficos de atividade

### 2. Team Detail — Agents Tab
**Problemas:**
- Cards de agente muito densos: timer, status, missão, tarefa, barra de contexto, provider, logs
- Grupos (coordenador, upstream, downstream) sem separação visual — apenas texto
- Sem indicador de dependência entre agentes
- Timer ocupa espaço mesmo quando agente está IDLE
- Barra de contexto é larga mas informação de pouca utilidade no dia-a-dia

**Oportunidade:** Colapsar informações secundárias, destacar status com cor de fundo do card, usar grid de 2 colunas para grupos

### 3. Team Detail — Mission Control Tab
**Problemas:**
- Mesma renderização do global, só filtrada — sem contexto do projeto
- Cards de missão colapsáveis mas sem indicador de prioridade
- Tasks dentro da missão usam muito espaço vertical

**Oportunidade:** Adicionar visão de timeline, destacar tasks bloqueadas

### 4. Global Mission Control
**Problemas:**
- Mistura missões de todos os projetos sem agrupamento visual forte
- Header com badges mas sumário ocupa espaço precioso
- Cards expansíveis sem estado de "expandido" persistente por sessão

### 5. Config
**Problemas:**
- Grid 2 colunas apertado em 1024px
- Provedores por agente vs API Keys vs Ollama — três conceitos diferentes no mesmo grid
- Campos de input de API Key lado a lado — fácil errar

## Propostas de Melhoria

### A) Hierarquia de Status com Cor de Fundo
Cada card de agente ganha uma borda lateral (4px) colorida com o status:
- RUNNING → cyan pulsante
- SUCCESS → verde
- FAILED → vermelho
- IDLE → sem borda (apenas glass)

### B) Cards Colapsáveis por Grupo
Grupos (coordenador, upstream, downstream) têm header clicável para
expandir/recolher. Cards dentro do grupo são grid 2 colunas.

### C) Timer Condicional
Timer só aparece quando agente está RUNNING. Quando IDLE, mostra "⏸️ Idle"
em texto menor.

### D) Config Reorganizada
Separar em abas: "Provedores" | "API Keys" | "Ollama". Cada aba com layout
dedicado, não grid forçado.

### E) Breadcrumb Navegável
Cada nível do breadcrumb é clicável: Home > Projeto > Tab > Agente

### F) Modal LLM com Header Contextual
Mostrar nome do agente e projeto no topo do modal, com avatar.

### G) Responsividade
Media queries para >1200px (3 colunas) e <768px (1 coluna).
