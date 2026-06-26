# Agent Factory — Manual para Agentes LLM

> Documentação técnica para agentes de IA consumirem durante automação.
> Cada seção é autocontida — consuma apenas o bloco relevante à sua tarefa.

---

## Índice

| # | Seção | Para que serve |
|---|-------|----------------|
| 1 | [O que é o Agent Factory](#1-o-que-é-o-agent-factory) | Contexto geral do framework |
| 2 | [Arquitetura do diretório](#2-arquitetura-do-diretório) | Onde cada coisa vive |
| 3 | [Adicionar um agente](#3-adicionar-um-agente) | Criar um novo agente do zero |
| 4 | [Alterar um agente](#4-alterar-um-agente) | Modificar lógica de agente existente |
| 5 | [Remover um agente](#5-remover-um-agente) | Desregistrar e remover agente |
| 6 | [Acionar um agente (execução)](#6-acionar-um-agente-execução) | Como executar tarefas em agentes |
| 7 | [AgentFactoryDevAgent](#7-agentfactorydevagent) | Agente auxiliar para automatizar seções 3-6 |

---

## 1. O que é o Agent Factory

Framework Python para **orquestração de agentes autônomos** com segregação de projetos, dashboard, persistência SQLite e integração com LLMs.

**Versão atual:** v1.1.0  
**Dependência principal:** `langgraph>=0.2.0`, `pydantic>=2.0.0`

### Conceitos-base

| Conceito | Descrição |
|----------|-----------|
| **Agente** | Classe que herda `AgentBase` e implementa `execute()` + `validate_input()` |
| **Projeto** | Escopo isolado (`ProjectConfig`) com seus próprios agentes, eventos e contexto |
| **EventNotifier** | Canal que emite eventos de agentes para dashboard + arquivos JSON |
| **Registry** | Registro centralizado de projetos (`ProjectRegistry`) |
| **Dashboard** | UI real-time via HTTP polling em `http://localhost:8080?project=<id>` |
| **ContextStore** | Persistência SQLite de contexto entre sessões |

---

## 2. Arquitetura do diretório

```
agent-factory/
├── src/
│   ├── agents/
│   │   ├── base.py          # AgentBase (ABC) + CoordinatorAgent
│   │   ├── real.py           # SubprocessAgent + LLMAgent
│   │   ├── factory_dev.py    # AgentFactoryDevAgent
│   │   └── __init__.py       # Exporta AgentBase, CoordinatorAgent, SubprocessAgent, LLMAgent
│   ├── protocols/
│   │   ├── schema.py         # Pydantic: AgentEvent, TaskResult, ProjectConfig, etc.
│   │   └── events.py         # EventNotifier
│   ├── persistence/
│   │   └── __init__.py       # ContextStore (SQLite)
│   ├── llm/
│   │   └── __init__.py       # LLM providers: Groq, Ollama, Mock
│   ├── dashboard/
│   │   ├── server.py         # ThreadingHTTPServer + API REST
│   │   └── index.html        # Dashboard UI
│   └── registry.py           # ProjectRegistry (singleton global)
├── projects/
│   └── pta/
│       ├── agents/
│       │   └── __init__.py   # Agentes específicos do PTA
│       ├── register.py       # Registro do projeto PTA
│       └── run.py            # Script de execução do PTA
├── docs/
│   ├── LLM_INSTRUCOES.md     # ← Este arquivo
│   └── GUIA_INICIALIZACAO.md # Setup do dashboard
├── start_dashboard.py        # Inicialização do dashboard
└── run_demo.py               # Demo minimalista
```

---

## 3. Adicionar um agente

### 3.1 Criar o arquivo do agente

Crie em `src/agents/<nome>.py`:

```python
"""
Agent Factory — MeuNovoAgente
"""
from typing import Any
from .base import AgentBase, AgentRole
from ..protocols.events import EventNotifier


class MeuNovoAgente(AgentBase):
    def __init__(self, project_id: str, notifier: EventNotifier):
        super().__init__(
            agent_id="meu-novo-agente",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
        )

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]
        if action == "fazer_algo":
            return {"status": "feito", "dado": task.get("param", None)}
        raise ValueError(f"Unknown action: {action}")
```

**Regras do `execute()`:**
- Recebe `task: dict` e retorna `dict`
- Emite eventos automaticamente via `self.notifier.emit()`
- Pode acessar `self.agent_id`, `self.project_id`, `self.role`

### 3.2 Exportar no `__init__.py`

Em `src/agents/__init__.py`, adicione:

```python
from .meu_novo_agente import MeuNovoAgente

__all__ = [
    "AgentBase",
    "CoordinatorAgent",
    "SubprocessAgent",
    "LLMAgent",
    "MeuNovoAgente",  # ← novo
]
```

### 3.3 Registrar no projeto

Em `projects/<projeto>/agents/__init__.py`:

```python
from src.agents.meu_novo_agente import MeuNovoAgente

# Adicionar ao dicionário PTA_AGENTS do projeto
PTA_AGENTS["meu-novo-agente"] = MeuNovoAgente
```

Ou programaticamente:

```python
from src.registry import get_registry

notifier = get_registry().get_notifier("pta")
agent = MeuNovoAgente("pta", notifier)
```

---

## 4. Alterar um agente

Edite o arquivo do agente em `src/agents/<nome>.py`:

| O que mudar | Onde |
|-------------|------|
| Lógica de `execute()` | Método `execute()` da classe |
| Validação de input | Método `validate_input()` |
| Ações disponíveis | Adicionar `elif action == "nova_acao"` no `execute()` |
| Nome/ID do agente | Parâmetro `agent_id` no `__init__` |
| Papel (role) | Parâmetro `role` no `__init__` (`WORKER`, `COORDINATOR`, `REVIEWER`) |

**Para exportar novo agente no `__init__.py`:**

```python
# Antes
from .agente_antigo import AgenteAntigo

# Depois
from .agente_novo import AgenteNovo
```

**Não é necessário reiniciar o servidor do dashboard** — as alterações são refletidas na próxima execução do agente (`run()`).

---

## 5. Remover um agente

### 5.1 Remover o arquivo

```bash
rm src/agents/<nome>.py
```

### 5.2 Limpar `__init__.py`

Remova a importação e o `__all__` entry em `src/agents/__init__.py`.

### 5.3 Remover do projeto

Remova a entrada do dicionário de agentes em `projects/<projeto>/agents/__init__.py`.

### 5.4 Desregistrar (se aplicável)

```python
from src.registry import get_registry

registry = get_registry()
# Projeto inteiro (remove todos agentes do projeto)
registry.unregister("project_id")
```

---

## 6. Acionar um agente (execução)

### 6.1 Diretamente (sem coordenador)

```python
from src.registry import get_registry

notifier = get_registry().get_notifier("pta")
agent = MeuNovoAgente("pta", notifier)

result = agent.run({
    "task_id": "minha-task-1",
    "action": "fazer_algo",
    "param": "valor",
})

print(result.status)       # AgentStatus.COMPLETED
print(result.output)       # dict com retorno do execute()
print(result.summary)      # Resumo legível
```

### 6.2 Via Coordenador (delegação)

```python
coordenador = get_pta_agent("coordenador", "pta", notifier)
coordenador.set_subordinates(agents_dict)

result = coordenador.run({
    "task_id": "task-orquestrada-1",
    "task_type": "cv_task",          # Define qual worker recebe
    "payload": {
        "task_id": "cv-subtask-1",
        "action": "detect_pose",
    },
})
```

**`task_type` disponíveis no PTA:**

| task_type | Worker alvo |
|-----------|-------------|
| `cv_task` | visao-computacional |
| `mobile_task` | frontend-mobile |
| `ui_task` | ui-ux |
| `qa_task` | qa |
| `render_task` | renderizacao |
| `body_mapping_v2` | Pipeline multi-fase |

**Formato simplificado** (inferência automática):

```python
coordenador.run({
    "task_id": "task-1",
    "message": "Classificar landmarks por tipo",
    # task_type será inferido como "cv_task"
})
```

### 6.3 Via SubprocessAgent (execução de código real)

```python
from src.agents.real import SubprocessAgent

agent = SubprocessAgent("executor", "pta", notifier)

result = agent.run({
    "task_id": "code-task-1",
    "code": "print('Olá mundo')",
    # ou "script": "caminho/para/script.py"
})
```

### 6.4 Via LLMAgent (decisão com IA)

```python
from src.agents.real import LLMAgent
from src.llm import get_provider

agent = LLMAgent(
    "analyst", "pta", notifier,
    provider=get_provider("groq"),
    system_prompt="Você é um analista.",
)

result = agent.run({
    "task_id": "llm-task-1",
    "prompt": "Analise estes dados...",
})
```

---

## 7. AgentFactoryDevAgent

Agente auxiliar que automatiza as seções 3-6 via tarefas.

**ID:** `agent-factory-dev`  
**Ações disponíveis:**

| Ação | Descrição |
|------|-----------|
| `create_agent` | Cria esqueleto de novo agente |
| `update_agent` | Marca alterações em agente existente |
| `register_agent` | Registra agente no projeto |
| `update_config` | Altera configuração do Agent Factory |
| `list_agents` | Lista todos agentes registrados |

**Exemplo de uso:**

```python
agent_factory_dev = AgentFactoryDevAgent("pta", notifier)

result = agent_factory_dev.run({
    "task_id": "dev-task-1",
    "action": "create_agent",
    "agent_id": "meu-novo-agente",
    "agent_class": "MeuNovoAgente",
    "description": "Agente que processa dados X",
})

result = agent_factory_dev.run({
    "task_id": "dev-task-2",
    "action": "list_agents",
})
```

---

## Convenções

- **IDs**: snake_case, hífen para separar palavras (`meu-novo-agente`)
- **Classes**: PascalCase (`MeuNovoAgente`)
- **Arquivos**: snake_case (`meu_novo_agente.py`)
- **Actions**: snake_case (`fazer_algo`)
- **Projetos**: sigla curta (`pta`, `demo`)

---

## Referência rápida de imports

```python
from src.agents.base import AgentBase, AgentRole, CoordinatorAgent
from src.agents.real import SubprocessAgent, LLMAgent
from src.agents.factory_dev import AgentFactoryDevAgent
from src.protocols.events import EventNotifier
from src.protocols.schema import AgentEvent, AgentStatus, TaskResult, ProjectConfig
from src.persistence import ContextStore
from src.llm import get_provider
from src.registry import get_registry, register_project
```
