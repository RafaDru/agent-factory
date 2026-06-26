# Agent Factory — Manual para Agentes LLM

> Documentação técnica para agentes de IA se orientarem durante automação.
> Cada seção é autocontida — consuma apenas o bloco relevante à sua tarefa.

---

## Índice

| # | Seção | Para que serve |
|---|-------|----------------|
| 1 | [O que é o Agent Factory](#1-o-que-é-o-agent-factory) | Contexto geral do framework |
| 2 | [Arquitetura do diretório](#2-arquitetura-do-diretório) | Onde cada coisa vive |
| 3 | [Criar um agente](#3-criar-um-agente) | Criar novo agente do zero |
| 4 | [Registrar e executar](#4-registrar-e-executar) | Como rodar agentes |
| 5 | [Pipeline (sequência de agentes)](#5-pipeline-sequência-de-agentes) | Playbook de execução |
| 6 | [ContextInjector](#6-contextinjector) | Preparar contexto entre passos |
| 7 | [LLMCache e CachedProvider](#7-llmcache-e-cachedprovider) | Evitar chamadas LLM repetidas |
| 8 | [OrchestratorGraph](#8-orchestratograph) | Pipeline LangGraph embutido |
| 9 | [Dashboard](#9-dashboard) | Monitoramento real-time |
| 10 | [ContextManager](#10-contextmanager) | Rastreamento de tokens/KB |
| 11 | [AgentLoader](#11-agentloader) | Carregar agentes sob demanda |
| 12 | [Convenções](#12-convenções) | Nomes, estilos, regras |

---

## 1. O que é o Agent Factory

Framework Python **v2.0.0-beta** para orquestração de agentes autônomos com segregação de projetos, dashboard real-time, rastreamento de contexto (tokens/KB), e integração com LLMs.

**Arquitetura:** Agent Factory é apenas a plataforma de execução. Agentes vivem em **projetos externos** e são carregados sob demanda via `AgentLoader`.

**Stack:** `langgraph>=0.2.0`, `pydantic>=2.0.0`, `groq`, `ollama`

### Conceitos-base

| Conceito | Descrição |
|----------|-----------|
| **AgentBase** | Classe abstrata que todo agente deve estender |
| **ContextManager** | Mede tokens e KB do contexto, auto-comprime >80% |
| **EventNotifier** | Emite eventos para JSONL + dashboard |
| **Pipeline** | Sequência pré-definida de agentes (playbook) |
| **ContextInjector** | Prepara/comprime contexto entre passos do pipeline |
| **LLMCache** | Cache de respostas LLM (exato + SQLite) |
| **AgentLoader** | Descobre e carrega agentes de projetos externos |
| **Dashboard** | UI web real-time com cards, barras de contexto, logs |

---

## 2. Arquitetura do diretório

```
agent-factory/
├── src/
│   ├── agents/
│   │   ├── base.py          # AgentBase (ABC), ContextManager, CoordinatorAgent
│   │   └── real.py          # SubprocessAgent, LLMAgent, ReviewerAgent
│   ├── protocols/
│   │   ├── schema.py        # Pydantic: AgentEvent, TaskResult, OrchestratorState
│   │   └── events.py        # EventNotifier (JSONL + SSE)
│   ├── persistence/         # ContextStore (SQLite)
│   ├── llm/                 # LLM providers: GroqProvider, OllamaProvider, MockProvider
│   ├── orchestrator/
│   │   ├── graph.py         # OrchestratorGraph (LangGraph: init→plan→execute→review→finalize)
│   │   ├── pipeline.py      # Pipeline declarativo com steps + placeholders
│   │   ├── context_injector.py # ContextInjector (select, truncate, summarize, compress)
│   │   └── cache.py         # LLMCache + CachedProvider wrapper
│   ├── dashboard/
│   │   ├── server.py        # ThreadingHTTPServer com API REST
│   │   └── index.html       # Dashboard dark mode com context bars
│   ├── registry.py          # ProjectRegistry (singleton)
│   └── loader.py            # AgentLoader (carrega agentes de projetos externos)
├── tests/                   # 56 testes pytest
├── examples/                # Exemplos de uso
├── projects/                # Configs de projetos externos
├── docs/
│   ├── LLM_INSTRUCOES.md    # ← Este arquivo
│   └── historico/           # Registro de alterações arquiteturais
├── pyproject.toml           # v2.0.0, MIT
├── start_dashboard.py       # Dashboard standalone
└── test_dashboard.py        # Dashboard + execução real
```

---

## 3. Criar um agente

### 3.1 Classe do agente

```python
"""
Agent Factory — MeuAgente
"""
from typing import Any
from src.agents.base import AgentBase, AgentRole
from src.protocols.events import EventNotifier


class MeuAgente(AgentBase):
    def __init__(self, project_id: str, notifier: EventNotifier):
        super().__init__(
            agent_id="meu-agente",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
        )

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]
        if action == "processar":
            return {"status": "ok", "data": task.get("payload")}
        raise ValueError(f"Ação desconhecida: {action}")
```

**Obrigatório no `execute()`:**
- Recebe `task: dict` e retorna `dict`
- Eventos são emitidos automaticamente via `self.notifier`
- Métricas de contexto são incluídas automaticamente nos eventos

### 3.2 Tipos de agente disponíveis

| Classe | Uso | Arquivo |
|--------|-----|---------|
| `AgentBase` | Classe base abstrata para agentes custom | `src/agents/base.py` |
| `CoordinatorAgent` | Delega tarefas a workers registrados | `src/agents/base.py` |
| `SubprocessAgent` | Executa código Python em subprocesso | `src/agents/real.py` |
| `LLMAgent` | Toma decisões via LLM (Groq/Ollama) | `src/agents/real.py` |
| `ReviewerAgent` | Revisa outputs de outros agentes | `src/agents/real.py` |

---

## 4. Registrar e executar

### 4.1 Registro de projeto

```python
from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
config = ProjectConfig(
    project_id="meu-projeto",
    name="Meu Projeto",
    description="Descrição",
)
project_id = registry.register(config)
notifier = registry.get_notifier(project_id)
```

### 4.2 Execução direta

```python
agent = MeuAgente("meu-projeto", notifier)
result = agent.run({
    "task_id": "task-1",
    "action": "processar",
    "payload": {"dado": "valor"},
})
print(result.status)  # AgentStatus.COMPLETED
print(result.output)  # dict com retorno do execute()
```

### 4.3 Via CoordinatorAgent

```python
from src.agents.base import CoordinatorAgent

coord = CoordinatorAgent("coord", "meu-projeto", notifier)
coord.set_subordinates({"worker-a": agente_a, "worker-b": agente_b})

result = coord.run({
    "task_id": "task-1",
    "task_type": "tipo_a",          # Define qual worker recebe
    "payload": {"action": "executar"},
})
```

### 4.4 Via SubprocessAgent (execução de código)

```python
from src.agents.real import SubprocessAgent

executor = SubprocessAgent("executor", "meu-projeto", notifier)
result = executor.run({
    "task_id": "code-1",
    "code": "print('hello')",
    # ou "script": "caminho/para/script.py"
})
```

### 4.5 Via LLMAgent (decisão com IA)

```python
from src.agents.real import LLMAgent
from src.llm import get_provider

analyst = LLMAgent(
    "analyst", "meu-projeto", notifier,
    provider=get_provider("groq"),
    system_prompt="Você é um analista de dados.",
)
result = analyst.run({
    "task_id": "llm-1",
    "prompt": "Analise estes dados: ...",
})
```

### 4.6 Com cache integrado (evita chamadas repetidas)

```python
from src.llm import get_provider
from src.orchestrator.cache import LLMCache, CachedProvider

cache = LLMCache(backend="sqlite", ttl=3600)
provider = CachedProvider(get_provider("groq"), cache)

analyst = LLMAgent("analyst", "meu-projeto", notifier, provider=provider)
```

---

## 5. Pipeline (sequência de agentes)

Define um playbook de execução: uma lista ordenada de steps, cada um mapeando um agente.

### 5.1 Uso básico

```python
from src.orchestrator.pipeline import Pipeline, PipelineStep

pipeline = Pipeline([
    PipelineStep(id="codegen", agent_id="executor",
                 input={"task_id": "gen-1", "spec": "{input.spec}"}),
    PipelineStep(id="qa",      agent_id="tester",
                 input={"task_id": "qa-1", "code": "{codegen.output.result}"}),
    PipelineStep(id="review",  agent_id="reviewer",
                 input={"task_id": "rv-1", "qa": "{qa.output.result}"},
                 on_failure="skip"),
])

result = pipeline.run(agents, {"spec": "Criar função de soma"})
# result.success, result.step_results, result.failed_steps
```

### 5.2 Placeholders

O input de cada step pode referenciar outputs de steps anteriores via `{step_id.field}`.

`{input.spec}` → valor do input inicial  
`{codegen.output.result}` → resultado do step "codegen"  
`{codegen.output.output.result}` → output.output do TaskResult

### 5.3 Políticas de falha

| Valor | Comportamento |
|-------|---------------|
| `"abort"` | (padrão) Para o pipeline todo |
| `"skip"` | Pula o step, continua os próximos |
| `"continue"` | Marca como falha mas continua |

### 5.4 Pipeline a partir de dict

```python
pipeline = Pipeline.from_dict([
    {"id": "a", "agent_id": "x", "input": {"task": "test"}},
    {"id": "b", "agent_id": "y", "input": {"prev": "{a.result}"}},
])
```

---

## 6. ContextInjector

Prepara o estado entre steps para evitar estouro de contexto.

### 6.1 Estratégias

| Estratégia | Descrição |
|---|---|
| `select` | Mantém só chaves relevantes (`keep_keys`) ou remove irrelevantes (`drop_keys`) |
| `truncate` | Corta textos por limite de caracteres/tokens |
| `summarize` | Usa LLM para resumir o estado preservando acordos |
| `compress` | Usa `ContextManager.compress_text()` |

### 6.2 Uso inline no Pipeline

```python
PipelineStep(id="qa_test", agent_id="tester",
    input={"code": "{codegen.output.result}"},
    inject={"strategy": "select", "keep_keys": ["input", "codegen"]},
)
```

### 6.3 Uso direto

```python
from src.orchestrator.context_injector import ContextInjector

injector = ContextInjector(llm_provider=my_llm)
state = injector.inject(state, {"strategy": "summarize", "max_tokens": 2000})
# Retorna: {"_summary": "...", "_strategy": "summarize"}
```

---

## 7. LLMCache e CachedProvider

Evita chamadas repetidas ao LLM para prompts já vistos.

### 7.1 Cache standalone

```python
from src.orchestrator.cache import LLMCache

cache = LLMCache(backend="sqlite", ttl=3600)  # ou "memory"

# Cache hit
response = cache.get(messages, "model-x", 0.7, 1024)
if response:
    print(response.content, "(cacheado)")

# Cache miss
cache.set(messages, "model-x", 0.7, 1024, llm_response)
```

### 7.2 CachedProvider (automático)

```python
from src.orchestrator.cache import LLMCache, CachedProvider
from src.llm import get_provider

cache = LLMCache(backend="memory", ttl=3600)
provider = CachedProvider(get_provider("groq"), cache)

# Transparente: hits retornam do cache, misses chamam a API
response = provider.chat(messages=[{"role": "user", "content": "Olá"}])
if response.usage.get("_cache") == "hit":
    print("Resposta do cache!")
```

### 7.3 Estatísticas

```python
stats = cache.stats()
# {"entries": 42, "total_hits": 150, "total_tokens_cached": 50000, "backend": "sqlite"}
```

---

## 8. OrchestratorGraph

Pipeline LangGraph embutido com nós fixos: `initialize → plan → execute → review → finalize`.

```python
from src.orchestrator.graph import OrchestratorGraph
from src.protocols.schema import ProjectConfig

config = ProjectConfig(project_id="meu-projeto", name="Meu Projeto")
orchestrator = OrchestratorGraph(config)

# Adicionar agentes ao grafo
orchestrator.add_agent(agent_a)
orchestrator.add_agent(agent_b)

# Executar
final_state = orchestrator.run({"tasks": [{"agent_id": "a", "task_id": "t1"}]})
```

O OrchestratorGraph itera sobre as tasks do estado e delega ao `agent_id` informado em cada task. Suporta ciclo de review com retry.

---

## 9. Dashboard

Dashboard web real-time em `http://localhost:8080?project=<id>`.

### Features do dashboard

- **Cards horizontais**: nome, role, status, ativações, última mensagem
- **Barra de contexto**: % real de tokens/KB com fallback por contagem de eventos
- **Event Log por agente**: paginado (10 itens), expansível dentro do card
- **Event Log global**: colapsável, com data/hora/agente/tarefa/status
- **Animações**: borda pulsante azul (running) ou vermelha (failed)
- **Context status**: bolinha colorida (ok/warning/exhausted) + KB usado/limite
- **Mini-chart**: barras das últimas 10 ativações

### Inicialização

```python
from src.dashboard.server import DashboardServer
from src.protocols.events import EventNotifier
from src.persistence import ContextStore

notifier = EventNotifier("meu-projeto")
store = ContextStore("meu-projeto")
server = DashboardServer(notifier, port=8080, context_store=store)
server.start()
```

---

## 10. ContextManager

Rastreia uso de contexto (tokens e KB) por agente com auto-compressão.

### 10.1 Uso

```python
from src.agents.base import ContextManager

cm = ContextManager(
    context_file=Path(".agent-context/meu-agente.json"),
    limit_kb=15.0,
    token_limit=128000,
    warn_at_percentage=80.0,
    auto_compress=True,
)

usage = cm.get_usage()
# {"used_kb": 2.3, "limit_kb": 15.0, "tokens": 580, "percentage": 15.3,
#  "status": "ok", "needs_compression": False, ...}
```

### 10.2 Dados incluídos em cada evento

```python
event.metrics.context = {
    "used_kb": 2.3,
    "limit_kb": 10.0,
    "tokens": 580,
    "token_limit": 2000,
    "percentage": 23.0,
    "status": "ok",          # "ok" | "warning" | "exhausted" | "no_context"
    "needs_compression": False,
}
```

### 10.3 Growth trend

```python
trend = cm.get_growth_trend()
# {"trend": "growing", "events_per_hour": 12.5,
#  "projected_exhaustion_in_hours": 8.3, "sample_size": 5}
```

---

## 11. AgentLoader

Carrega agentes sob demanda de projetos externos.

```python
from src.loader import AgentLoader

# Carregar agente de projeto externo
agent = AgentLoader.load("meu-projeto", "meu-agente")
# AgentLoader descobre o arquivo, importa, instancia e retorna

# Registrar referência para carregamento lazy
from src.registry import get_registry
registry = get_registry()
refs = registry.list_agent_refs("meu-projeto")
```

---

## 12. Convenções

| Regra | Padrão | Exemplo |
|-------|--------|---------|
| IDs de agente | snake_case com hífen | `meu-agente`, `visao-computacional` |
| Nomes de classe | PascalCase | `MeuAgente`, `SubprocessAgent` |
| Nomes de arquivo | snake_case | `meu_agente.py` |
| Actions | snake_case | `processar_dados`, `detectar_pose` |
| IDs de projeto | sigla curta | `pta`, `demo`, `meu-projeto` |
| Task IDs | prefixo + número | `cv-1`, `mobile-2`, `qa-3` |

### Imports rápidos

```python
from src.agents.base import AgentBase, AgentRole, CoordinatorAgent, ContextManager
from src.agents.real import SubprocessAgent, LLMAgent, ReviewerAgent
from src.protocols.events import EventNotifier
from src.protocols.schema import AgentEvent, AgentStatus, TaskResult, ProjectConfig
from src.persistence import ContextStore
from src.llm import get_provider, LLMProvider
from src.registry import get_registry
from src.loader import AgentLoader
from src.orchestrator.pipeline import Pipeline, PipelineStep, PipelineResult
from src.orchestrator.context_injector import ContextInjector, InjectorConfig
from src.orchestrator.cache import LLMCache, CachedProvider
from src.orchestrator.graph import OrchestratorGraph
```
