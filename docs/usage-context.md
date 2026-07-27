# Contexto de Uso — Agent Factory Platform

## Personas

### 1. Usuário Final / Operador
- Acessa o Dashboard (http://localhost:8080)
- Quer ver rapidamente: quais projetos existem, quantos agentes estão rodando, status das missões
- Monitora execuções em tempo real via Mission Control
- Configura provedores LLM e API Keys
- Navega entre projetos e agentes

### 2. Desenvolvedor / Configurador
- Gerencia times de agentes por projeto
- Atribui provedores LLM a cada agente
- Testa conectividade com APIs (Groq, OpenAI, Ollama)
- Acompanha logs de execução por agente
- Ajusta design systems e protótipos

### 3. AI Agent (Coordinator)
- Orquestra workers via Event Bus (RabbitMQ)
- Cria planos com DAG de tarefas
- Delega para workers e coleta resultados
- Não usa UI diretamente — interage via MCP/RabbitMQ

### 4. AI Agent (Workers: dev, qa, designer, etc.)
- Executa tarefas específicas
- Reporta resultados e erros estruturados
- Consome tarefas da fila RabbitMQ
- Não usa UI diretamente — interage via MCP/RabbitMQ

## Fluxos de Navegação

### Home → Projetos
```
/ → Lista de projetos (cards)
  ├── Clica no card → /project/{id}/agents (Team Detail)
  ├── Select dropdown → /project/{id}/agents
  └── Header: Home | Mission Control | Config
```

### Team Detail
```
/project/{id}/agents
  ├── Tab AGENTS → cards de agentes com status, timer, provider
  ├── Tab Mission Control → missões do projeto
  ├── Cada card de agente:
  │   ├── Botão LLM → abre modal de seleção de provider
  │   ├── Botão 📋 → abre Logs Panel filtrado
  │   └── Timer, status, última execução
  └── Botão ⚙️ Config → config global
```

### Mission Control (Global)
```
/mission-control
  ├── Header com badges: running, blocked, total
  ├── Sumário: concluídas, falhas, executando
  └── Missões agrupadas por projeto (cards colapsáveis)
      └── Cada card tem tasks com status individual
```

### Config
```
/config
  ├── Provedores por Agente (grid 2 colunas)
  │   └── Lista de agentes por projeto com botão de provider
  ├── API Keys (add/remove)
  └── Ollama Auto-Discovery (scan local models)
```

## Dados Exibidos

### Projeto
- nome, id, contagem de agentes, contagem de ativos

### Agente (no card)
- avatar (emoji), nome, role
- status: IDLE (cinza), RUNNING (azul), SUCCESS (verde), FAILED (vermelho)
- última tarefa: nome, status, duração, timestamp
- LLM provider configurado
- timer de execução (HH:MM:SS) quando running
- barra de contexto (uso de tokens)
- missão atual + nome da tarefa

### Missão
- id, objetivo, status (running/completed/failed/blocked)
- progresso (X/Y tasks concluídas)
- timestamps de início/fim
- tasks com dependências, status, agente designado

## Problemas Observados na UI Atual

1. **Cards de agentes densos demais** — muita informação num card só (timer, status, provider, missão, tarefa, barra de contexto, log, última execução)
2. **Hierarquia visual fraca** — cores neon competem com badges de status, difícil escanear rapidamente
3. **Team Detail sem indentação de grupos** — coordenador, upstream, downstream são apenas labels, sem separação visual clara
4. **Config densa** — grid 2 colunas apertado, provedores misturados com API Keys e Ollama
5. **Sem onboarding** — novo usuário não sabe o que cada view faz
6. **Logs panel** — painel separado, mas não integrado visualmente ao card do agente
7. **Modal LLM** — funcional mas sem indicação visual de qual agente está sendo configurado no header do modal
8. **Breadcrumb subutilizado** — mostra caminho mas não é clicável em todos os níveis
9. **Responsividade** — layout quebra em telas menores (<1024px)
10. **Cores** — ciano e roxo dominam, mas sem função semântica clara
