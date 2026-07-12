# Agent Factory — MCP Server + Coordenador com LLM + Projeto Solar

**Data**: 2026-07-10
**Sessão**: OpenCode (Rafael + AI Agent)
**Status**: Concluída

---

## O que foi feito

### 1. AGENTS.md — Arquitetura Oficial
- Documento de entrada para AI agents que aterrissam no projeto
- Fluxo completo de delegação recursiva: Usuário → OpenCode → MCP → Coordenador → Workers
- Dois modos de execução: MCP Tool Call (síncrono) e Autonomous Session (sub-sessão LLM)
- Conceitos: Session, MCP Server, Coordinator, Worker, Context File, StructuredError
- Ciclo de erro: `StructuredError` → `available_actions` → retry

### 2. MCP Server (`src/mcp/server.py`)
- Usa `FastMCP` do pacote `mcp` v1.28.1
- **6 tools**: `list_projects`, `list_agents`, `run_agent`, `run_objective`, `read_events`, `get_project_status`
- **4 resource templates**: `afp://{project}/events`, `/agents`, `/{agent}/context`, `/{agent}/capabilities`
- Transporte SSE em `http://127.0.0.1:8081/sse`
- Inicializado via `--mcp` flag no `start_agent_factory.py`
- Auto-wiring de subordinados: quando `run_objective` ou `run_agent` carregam o coordenador, automaticamente carrega e conecta `agent-factory-dev` e `qa` como subordinados

### 3. Coordenador com LLM (`src/agents/coordinator.py`)
- `AgentFactoryCoordinator` agora aceita `llm_provider` opcional (default: `get_provider("auto")`)
- `_plan_with_llm()`: gera plano de tarefas via LLM a partir de objetivo em linguagem natural
- Dois modos de `plan_and_execute`:
  - **Modo 1 (LLM)**: fornece apenas `goal` + opcional `context`, coordenador chama LLM para gerar o plano
  - **Modo 2 (manual)**: fornece `tasks` explicitamente, executa direto (compatibilidade retroativa)
- System prompt (`PLAN_SYSTEM_PROMPT`) descreve subordinados, ações, parâmetros e formato JSON esperado
- Parse do JSON do LLM com suporte a blocos ```json
- `StructuredError` para: `llm_error`, `invalid_plan_json`, `empty_plan`, `missing_goal`

### 4. Smoke Tests
- `test_mcp_smoke.py`: valida todas as 6 tools + 4 resources
- `test_coordinator_llm.py`: valida geração de plano via LLM
- `test_full_mcp.py`: valida ciclo completo MCP → coordenador → LLM → workers
- Todos passando

### 5. Documentação Atualizada
- `README.md`: seção MCP com tools, resources e comando `--mcp`
- `AGENTS.md`: arquitetura completa com MCP e delegação recursiva
- `docs/LLM_INSTRUCOES.md`: nova seção 13 sobre MCP Server
- `contexts/agent-factory-dev/coordenador/CONTEXTO.md`: Modo 1 (LLM) e Modo 2 (manual)

---

## Estado Atual da Plataforma

### Servidores (background)
| Serviço | Porta | Comando |
|---------|-------|---------|
| Dashboard | 8080 | `start_agent_factory.py --mcp` |
| MCP Server (SSE) | 8081 | `start_agent_factory.py --mcp` |
| Ollama | 11434 | Gerenciado pelo startup |

### Projetos Registrados
| Projeto | Agentes | Finalidade |
|---------|---------|------------|
| `agent-factory-dev` | coordenador, agent-factory-dev, qa | Evoluir a plataforma AFP |
| `pta` | 8 agentes (coordenador, frontend-mobile, visao-computacional, etc.) | Personal Trainer App |

### Modelos Locais (Ollama)
| Modelo | Params | Função |
|--------|--------|--------|
| `gemma3:4b` | 4.3B | Classificador rápido |
| `qwen2.5-coder:7b` | 7.6B | Geração de código |
| `gemma4` | 8B | Validação |
| `qwen3.6` | 36B MoE | Raciocínio pesado |

### Provedor LLM Padrão
- `get_provider("auto")`: tenta Groq → Ollama (`MultiModelProvider`) → Mock
- `MultiModelProvider` classifica a tarefa com `gemma3:4b` e roteia para o modelo especialista
- Hoje sem `GROQ_API_KEY`, usa apenas Ollama local

---

## Fluxo de Execução (validado)

```
MCP run_objective("Listar arquivos Python em src/")
  → MCP server carrega coordenador do registry
  → Auto-wiring: conecta agent-factory-dev e qa como subordinados
  → Coordenador recebe task com action=plan_and_execute, goal="Listar arquivos..."
  → Sem tasks explicitas, chama _plan_with_llm()
  → LLM (qwen2.5-coder:7b via MultiModelProvider) gera plano JSON
  → Coordenador executa DAG: delega list_directory para agent-factory-dev
  → Resultado: "3 arquivos encontrados" + detalhes
  → Sobe pela cadeia: Worker → Coordenador → MCP → Cliente
```

---

## Decisões de Arquitetura

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| Transporte MCP | SSE (HTTP) | Mais fácil de debugar que stdio; OpenCode suporta ambos |
| Provedor LLM | `auto` (MultiModelProvider) | Aproveita squad de 4 modelos locais com roteamento inteligente |
| Plano via LLM vs manual | Ambos suportados | LLM para autonomia, manual para controle explícito |
| Auto-wiring | MCP carrega subordinados | Evita depender de `set_subordinates()` manual |
| Contexto dos agentes | `contexts/<projeto>/<agente>/CONTEXTO.md` | Versionado no git, incrementável por sessão |

---

## Próximo Framework: Projeto Solar (Usina Fotovoltaica)

### Contexto
Rafael tem uma usina solar residencial que gera dados de produção de energia.
Existe um projeto simples rodando na máquina que monitora esses resultados.

### Objetivo
Criar um time temporário de agentes no AFP para otimizar e evoluir este projeto.

### Informações Pendentes (coletar na próxima sessão)
- [ ] Caminho do projeto no disco
- [ ] Stack atual (linguagem, frameworks, banco)
- [ ] O que o projeto faz (coleta, armazena, exibe)
- [ ] O que otimizar (performance, UX, features, automação)
- [ ] Agentes necessários (ex: solar-dev, solar-qa, solar-coordenador)

---

## Pendências

| Item | Status |
|------|--------|
| Spawn de sessão (worker como mini-LLM) | ⏳ Passo 4 da roadmap |
| MCP com parâmetro de modelo | ⏳ Melhoria |
| Testes unitários do coordenador com LLM mock | ⏳ Pendente |
| Projeto Solar: configuração no AFP | ✅ Concluído |
| Projeto Solar: primeira tarefa (negócios analisa) | ✅ Concluído |
| System Tray Icon para Windows | 🔜 Próxima prioridade |

## Feature Request: System Tray Icon

Registrado em `AGENTS.md` na seção "Feature Roadmap (Solicitado pelo Usuario)".

**Objetivo:** Icone na bandeja do sistema com:
- Status visual (rodando/parado)
- Atalho para abrir Dashboard
- Liga/Desliga do servidor AFP
- Inicialização automática com Windows
- Notificações toast de eventos dos agentes
- Menu de contexto com ações rápidas
