import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.registry import get_registry
from src.protocols.schema import AgentStatus
from src.mcp.event_bus import call_agent_via_event_bus, event_bus_available

CONTEXT_TEMPLATE_COORD = """# {agent_id} — {project_name}

## Proposito
{description}

## Subordinados Disponiveis
{subordinates_section}

## Acoes Disponiveis
| Acao | Descricao |
|------|-----------|
| plan_and_execute | Recebe objetivo, gera plano via LLM e executa DAG de tarefas |
| delegate | Delega tarefa para subordinado e retorna resultado |
| get_capabilities | Retorna as acoes disponiveis neste agente |

## Exemplos
```json
{{"action": "plan_and_execute", "goal": "Analisar codigo e sugerir melhorias", "context": "..."}}
```

## Working Directory
`{working_dir}`"""

CONTEXT_TEMPLATE_WORKER = """# {agent_id} — {project_name}

## Proposito
{description}

## Acoes Disponiveis
| Acao | Descricao |
|------|-----------|
{actions_table}

## Exemplos
```json
{{"action": "execute", "param": "value"}}
```

## Working Directory
`{working_dir}`"""

DEFAULT_ACTIONS = {
    "dev": [
        ("read_file", "Le conteudo de um arquivo"),
        ("write_file", "Escreve conteudo em um arquivo"),
        ("edit_file", "Edita um arquivo (substitui trecho)"),
        ("generate_code", "Gera codigo via LLM"),
        ("implement_feature", "Planeja e implementa feature via LLM"),
    ],
    "qa": [
        ("run_tests", "Executa pytest"),
        ("validate_python_syntax", "Valida sintaxe Python"),
        ("review_code", "Revisa codigo via LLM"),
        ("analyze_artifact", "Analisa artefato do disco"),
        ("file_exists", "Verifica existencia de arquivo"),
    ],
    "designer": [
        ("research_design_systems", "Pesquisa design systems"),
        ("analyze_ux", "Analisa UX/UI"),
        ("design_ui", "Cria propostas de UI"),
        ("prototype", "Gera prototipo HTML/CSS"),
    ],
    "default": [
        ("execute", "Executa tarefa principal"),
        ("get_capabilities", "Retorna capacidades"),
    ],
}

AGENT_EMOJIS = {
    "coordenador": "🎯", "dev": "⚙️", "qa": "🧪", "designer": "🎨",
    "negocios": "💼", "desenvolvedor": "⚙️", "design": "🎨",
    "klipper": "🔌", "pipeline": "📐", "visao": "👁️", "resume": "🔄",
}

mcp = FastMCP(
    "Agent Factory Platform",
    instructions="""Agent Factory Platform (AFP) — expose agentes como ferramentas para LLMs.
    
    Use `list_projects` para descobrir projetos registrados.
    Use `list_agents` para ver agentes e suas capacidades.
    Use `run_agent` para executar tarefas em agentes especificos.
    Use `run_objective` para delegar objetivos de alto nivel ao coordenador.
    
    Os agentes retornam StructuredError em caso de falha, com `error_type`,
    `available_actions`, e `hint` para que voce possa corrigir e tentar novamente.""",
)


def _get_registry():
    return get_registry()


def _wire_subordinates(registry, project_id: str, agent):
    """Carrega e conecta subordinados ao coordenador."""
    # Load agent_config.json for LLM provider overrides
    agent_config_map = {}
    try:
        import json as _json
        cfg_path = Path(".agent-factory/agent_config.json")
        if cfg_path.exists():
            agent_config_map = _json.loads(cfg_path.read_text())
    except Exception:
        pass

    subordinates = {}
    refs = registry.list_agent_refs(project_id)
    for aid in refs:
        if aid == "coordenador":
            continue
        try:
            subordinate = registry.load_agent(project_id, aid)
            # Set LLM provider from agent_config.json if available (overrides config file)
            sub_cfg = agent_config_map.get(aid, {})
            provider_str = sub_cfg.get("llm_provider")
            if provider_str and hasattr(subordinate, '_llm'):
                from src.llm import get_provider
                try:
                    prov = get_provider(provider_str)
                    subordinate._llm = prov
                    if hasattr(subordinate, '_llm_provider'):
                        subordinate._llm_provider = prov
                except Exception:
                    pass
            subordinates[aid] = subordinate
            print(f"  [MCP] Worker carregado: {aid} ({type(subordinate).__name__})")
        except Exception as e:
            print(f"  [MCP] Worker {aid} nao carregado: {e}")
    if subordinates:
        agent.set_subordinates(subordinates)


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_projects() -> list[dict[str, Any]]:
    """Lista todos os projetos registrados no Agent Factory.

    Returns:
        Lista de projetos com id, nome, descricao e agentes registrados.
    """
    registry = _get_registry()
    projects = []
    for config in registry.list_projects():
        refs = registry.list_agent_refs(config.project_id)
        projects.append({
            "project_id": config.project_id,
            "name": config.name,
            "description": config.description,
            "agents": list(refs.keys()),
        })
    return projects


@mcp.tool()
def list_agents(project_id: str) -> list[dict[str, Any]]:
    """Lista agentes de um projeto com suas capacidades.

    Args:
        project_id: ID do projeto (ex: "afp", "pta")

    Returns:
        Lista de agentes com id, class_name, context_limit_kb e actions.
    """
    registry = _get_registry()
    refs = registry.list_agent_refs(project_id)
    if not refs:
        return []
    agents = []
    for agent_id, ref in refs.items():
        info = {
            "agent_id": ref.agent_id,
            "class_name": ref.class_name,
            "module_path": str(ref.module_path),
            "context_limit_kb": ref.context_limit_kb,
            "context_file": ref.context_file,
        }
        try:
            agent = registry.load_agent(project_id, agent_id)
            capabilities = agent.get_capabilities()
            info["capabilities"] = capabilities
        except Exception as e:
            info["error"] = str(e)
        agents.append(info)
    return agents


@mcp.tool()
def run_agent(
    project_id: str,
    agent_id: str,
    task: dict[str, Any],
) -> dict[str, Any]:
    """Executa uma tarefa em um agente especifico.

    Tenta via Event Bus (RabbitMQ) primeiro. Se o runtime do agente
    nao estiver disponivel, carrega e executa in-process (fallback).

    Args:
        project_id: ID do projeto (ex: "afp", "pta")
        agent_id: ID do agente (ex: "dev", "qa", "coordenador")
        task: Dicionario com a tarefa. Deve conter no minimo "action" e
              os parametros especificos da acao.

    Returns:
        Resultado da execucao com status, output e metricas.
    """
    # Tentar via Event Bus (RabbitMQ)
    if event_bus_available():
        event_bus_task = dict(task)
        event_bus_task["_project_id"] = project_id
        result = call_agent_via_event_bus(agent_id, event_bus_task, timeout=120.0)
        if result:
            return _format_event_bus_result(result)

    # Fallback: in-process
    registry = _get_registry()
    try:
        agent = registry.load_agent(project_id, agent_id)
    except ValueError as e:
        return {
            "error_type": "agent_not_found",
            "message": str(e),
            "project_id": project_id,
            "agent_id": agent_id,
        }

    if agent_id == "coordenador" and hasattr(agent, "set_subordinates"):
        _wire_subordinates(registry, project_id, agent)

    try:
        result = agent.run(task)
        return {
            "status": result.status.value,
            "task_id": result.task_id,
            "output": result.output,
            "summary": result.summary,
            "duration_ms": result.total_duration_ms,
            "metrics": result.metrics,
        }
    except Exception as e:
        payload = getattr(e, "to_dict", lambda: None)()
        if payload:
            return payload
        return {
            "error_type": "execution_error",
            "message": str(e),
            "action_requested": task.get("action"),
        }


def _format_event_bus_result(result: dict) -> dict:
    """Formata resultado do Event Bus para o padrao MCP."""
    output = result.get("result", {})
    if isinstance(output, dict):
        return {
            "status": result.get("status", "ok"),
            "output": output.get("output", output),
            "summary": output.get("summary", output.get("rationale", "")),
            "transport": "event_bus",
        }
    return {
        "status": result.get("status", "ok"),
        "output": output,
        "summary": str(output)[:200],
        "transport": "event_bus",
    }


@mcp.tool()
def run_objective(
    project_id: str,
    objective: str,
    context: str = "",
) -> dict[str, Any]:
    """Envia um objetivo de alto nivel para o coordenador do projeto.

    Tenta via Event Bus (RabbitMQ) primeiro. Se o runtime do coordenador
    nao estiver disponivel, carrega e executa in-process (fallback).

    Args:
        project_id: ID do projeto (ex: "afp")
        objective: Descricao do objetivo em linguagem natural
        context: Contexto adicional ou restricoes para a execucao

    Returns:
        Resultado consolidado com plano, execucoes individuais e status final.
    """
    task = {
        "task_id": f"obj-{abs(hash(objective)) % 10000:04d}",
        "action": "plan_and_execute",
        "goal": objective,
        "context": context,
    }

    # Tentar via Event Bus (RabbitMQ)
    if event_bus_available():
        event_bus_task = dict(task)
        event_bus_task["_project_id"] = project_id
        result = call_agent_via_event_bus("coordenador", event_bus_task, timeout=300.0)
        if result:
            return _format_event_bus_result(result)

    # Fallback: in-process
    registry = _get_registry()
    try:
        agent = registry.load_agent(project_id, "coordenador")
    except ValueError as e:
        return {
            "error_type": "coordinator_not_found",
            "message": str(e),
            "project_id": project_id,
        }

    # Set LLM provider from agent_config.json if available
    try:
        import json as _json
        cfg_path = Path(".agent-factory/agent_config.json")
        if cfg_path.exists():
            cfg = _json.loads(cfg_path.read_text())
            coord_cfg = cfg.get("coordenador", {})
            provider_str = coord_cfg.get("llm_provider") or coord_cfg.get("llm_provider", "")
            if provider_str:
                from src.llm import get_provider
                from src.agents.base import CoordinatorAgent
                if isinstance(agent, CoordinatorAgent):
                    agent.llm_provider = get_provider(provider_str)
                    agent._llm = agent.llm_provider
    except Exception as e:
        print(f"  [MCP] Aviso: nao foi possivel configurar LLM do coordenador: {e}")

    _wire_subordinates(registry, project_id, agent)

    try:
        result = agent.run(task)
        return {
            "status": result.status.value,
            "task_id": result.task_id,
            "output": result.output,
            "summary": result.summary,
            "duration_ms": result.total_duration_ms,
        }
    except Exception as e:
        payload = getattr(e, "to_dict", lambda: None)()
        if payload:
            return payload
        return {
            "error_type": "objective_error",
            "message": str(e),
            "objective": objective,
        }


@mcp.tool()
def read_events(project_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Le eventos recentes de um projeto.

    Args:
        project_id: ID do projeto
        limit: Numero maximo de eventos (padrao: 50)

    Returns:
        Lista de eventos com agent_id, status, message e timestamp.
    """
    registry = _get_registry()
    notifier = registry.get_notifier(project_id)
    if not notifier:
        return []
    events = notifier.get_events()
    return [
        {
            "agent_id": e.agent_id,
            "status": e.status.value,
            "task_id": e.task_id,
            "message": e.message,
            "timestamp": e.timestamp,
            "duration_ms": e.metrics.get("duration_ms") if e.metrics else None,
        }
        for e in events[-limit:]
    ]


@mcp.tool()
def get_project_status(project_id: str) -> dict[str, Any]:
    """Retorna status consolidado de um projeto.

    Args:
        project_id: ID do projeto

    Returns:
        Status com agentes, total de eventos, sucessos e falhas.
    """
    registry = _get_registry()
    return registry.get_project_status(project_id)


@mcp.tool()
def figma_get_file(file_key: str) -> dict[str, Any]:
    """Obtem metadados de um arquivo Figma via REST API.

    Usa FIGMA_API_KEY do ambiente. Retorna nome, versao, ultima modificacao
    e lista de paginas/documentos do arquivo.

    Args:
        file_key: A chave do arquivo Figma (da URL: figma.com/file/KEY/...)

    Returns:
        Dados do arquivo Figma com documento e paginas.
    """
    api_key = os.getenv("FIGMA_API_KEY")
    if not api_key:
        return {"error": "FIGMA_API_KEY nao configurada no ambiente"}
    url = f"https://api.figma.com/v1/files/{file_key}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": api_key})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {
                "name": data.get("name", ""),
                "version": data.get("version", ""),
                "last_modified": data.get("lastModified", ""),
                "pages": [
                    {"id": d.get("id"), "name": d.get("name")}
                    for d in (data.get("document", {}).get("children", []))
                ],
            }
    except urllib.error.HTTPError as e:
        return {"error": f"Figma API HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# ── Project Creation Tools ────────────────────────────────────────────────────


@mcp.tool()
def register_project(
    project_id: str = "",
    name: str = "",
    description: str = "",
    agents: list[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Registra um novo projeto no Agent Factory. QUESTIONARIO INTERATIVO.

    Use esta ferramenta como um assistente passo-a-passo para criar projetos.
    Se campos estiverem vazios, a ferramenta retorna perguntas para preencher.

    PASSO 1: Chame com project_id vazio "" -> retorna instrucoes iniciais
    PASSO 2: Forneca project_id, name, description
    PASSO 3: Forneca agents (lista de agentes com agent_id, description, type)
    PASSO 4: Ferramenta cria tudo e retorna confirmacao

    Args:
        project_id: ID curto do projeto (ex: "meu-app", "chatbot-ai")
        name: Nome completo do projeto (ex: "Meu App com IA")
        description: Descricao do que o time de agentes vai fazer
        agents: Lista de agentes. Cada agente: {agent_id, description, type}
                type pode ser: "coordenador", "dev", "qa", "designer", "custom"

    Returns:
        Instrucoes do proximo passo ou confirmacao de criacao.
    """
    if not agents:
        agents = []

    # PASSO 1: Sem project_id - retornar instrucoes
    if not project_id:
        return {
            "step": 1,
            "title": "Criar Novo Projeto - Questionario",
            "message": "Vou te guiar na criacao de um time de agentes. Responda as perguntas abaixo:",
            "questions": [
                {"field": "project_id", "question": "Qual o ID curto do projeto? (ex: 'chatbot-ai', 'ecommerce')", "example": "meu-app", "required": True},
                {"field": "name", "question": "Qual o nome completo do projeto?", "example": "Chatbot com IA Generativa", "required": True},
                {"field": "description", "question": "O que o time de agentes vai fazer neste projeto?", "example": "Desenvolver um chatbot com IA para atendimento ao cliente", "required": True},
            ],
            "next_step": "Responda com project_id, name e description para continuar.",
        }

    # PASSO 2: Tem project_id mas sem agents - pedir agents
    if not agents:
        return {
            "step": 2,
            "title": f"Projeto '{project_id}' - Definir Agentes",
            "project_so_far": {"project_id": project_id, "name": name or project_id, "description": description or ""},
            "message": "Agora defina os agentes do time. Voce pode usar tipos pre-definidos ou customizados.",
            "agent_types": {
                "coordenador": "Orquestrador: planeja via LLM e delega tarefas",
                "dev": "Desenvolvedor: codigo, arquivos, scripts, git, LLM",
                "qa": "QA: testes, revisao de codigo, qualidade",
                "designer": "Designer: pesquisa design systems, prototipos, UX",
                "custom": "Agente customizado com capacidades basicas",
            },
            "example_agents": [
                {"agent_id": "coordenador", "description": "Orquestrador do time", "type": "coordenador"},
                {"agent_id": "dev", "description": "Desenvolvedor principal", "type": "dev"},
                {"agent_id": "qa", "description": "Qualidade e testes", "type": "qa"},
            ],
            "next_step": "Forneca a lista de agents com agent_id, description e type.",
        }

    # PASSO 3: Criar tudo
    registry = _get_registry()
    if registry.project_exists(project_id):
        return {"step": "error", "error": f"Projeto '{project_id}' ja existe. Use add_agent para adicionar agentes."}

    contexts_base = Path("contexts") / project_id
    contexts_base.mkdir(parents=True, exist_ok=True)

    from src.protocols.schema import ProjectConfig
    registry.register(ProjectConfig(project_id=project_id, name=name or project_id, description=description or ""))

    created_agents = []
    has_coordinator = any(a.get("type") == "coordenador" or a.get("agent_id") == "coordenador" for a in agents)

    for agent_data in agents:
        agent_id = agent_data.get("agent_id", "")
        agent_type = agent_data.get("type", "custom")
        agent_desc = agent_data.get("description", f"Agente {agent_id}")
        emoji = AGENT_EMOJIS.get(agent_id, AGENT_EMOJIS.get(agent_type, "🤖"))
        if not agent_id:
            continue

        agent_dir = contexts_base / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        if agent_type == "coordenador" or agent_id == "coordenador":
            sub_ids = [a.get("agent_id") for a in agents if a.get("agent_id") != "coordenador"]
            sub_section = "\n".join(f"### {sid}\nSem descricao definida." for sid in sub_ids) if sub_ids else "### (sem subordinados ainda)"
            context_content = CONTEXT_TEMPLATE_COORD.format(agent_id=agent_id, project_name=name or project_id, description=agent_desc, subordinates_section=sub_section, working_dir=str(Path.cwd()))
        else:
            actions = DEFAULT_ACTIONS.get(agent_type, DEFAULT_ACTIONS["default"])
            actions_table = "\n".join(f"| {a[0]} | {a[1]} |" for a in actions)
            context_content = CONTEXT_TEMPLATE_WORKER.format(agent_id=agent_id, project_name=name or project_id, description=agent_desc, actions_table=actions_table, working_dir=str(Path.cwd()))

        ctx_file = agent_dir / "CONTEXTO.md"
        ctx_file.write_text(context_content, encoding="utf-8")
        created_agents.append({"agent_id": agent_id, "type": agent_type, "context_file": str(ctx_file), "emoji": emoji})

    project_json = {
        "project_id": project_id,
        "project_name": name or project_id,
        "team_id": project_id + "-Team",
        "team_name": (name or project_id) + " Team",
        "description": description or "",
        "icon": "📦",
        "working_dir": str(Path.cwd()),
        "agents_source": "src/agents/",
        "agents": [
            {
                "agent_id": a["agent_id"],
                "module_path": f"src/agents/{project_id}_{a['agent_id']}.py",
                "class_name": f"{project_id.title().replace('-','')}{a['agent_id'].title().replace('-','')}",
                "context_limit_kb": 10.0,
                "llm_provider": "auto",
                "emoji": AGENT_EMOJIS.get(a.get("agent_id",""), AGENT_EMOJIS.get(a.get("type",""), "🤖")),
                "description": a.get("description", ""),
            }
            for a in agents
        ],
    }
    (contexts_base / "project.json").write_text(json.dumps(project_json, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "step": "complete", "status": "created",
        "project": {"project_id": project_id, "name": name or project_id},
        "agents_created": len(created_agents), "agents": created_agents,
        "files_created": [str(contexts_base / "project.json")] + [str(contexts_base / a["agent_id"] / "CONTEXTO.md") for a in created_agents],
        "next_steps": [
            "Implemente as classes Python dos agentes em src/agents/",
            "Reinicie o Agent Factory para o auto-discovery registrar o projeto",
            "Use add_agent para adicionar mais agentes depois",
        ],
    }
    if not has_coordinator:
        result["warning"] = "Nenhum agente 'coordenador' definido. Adicione um para usar run_objective."
    return result


@mcp.tool()
def add_agent(project_id: str, agent_id: str = "", description: str = "", agent_type: str = "custom") -> dict[str, Any]:
    """Adiciona um novo agente a um projeto existente. QUESTIONARIO.

    PASSO 1: Chame com agent_id vazio -> retorna agentes existentes e pergunta
    PASSO 2: Forneca agent_id, description, agent_type -> cria o agente

    Args:
        project_id: ID do projeto existente
        agent_id: ID do novo agente (ex: "devops", "security")
        description: O que este agente faz
        agent_type: Tipo pre-definido ou "custom"
    Returns:
        Instrucoes ou confirmacao da criacao.
    """
    registry = _get_registry()
    if not registry.project_exists(project_id):
        return {"error": f"Projeto '{project_id}' nao encontrado.", "available_projects": [p.project_id for p in registry.list_projects()], "hint": "Use list_projects() para ver projetos disponiveis."}

    existing = registry.list_agent_refs(project_id)
    if not agent_id:
        return {
            "step": 1, "project_id": project_id,
            "existing_agents": list(existing.keys()) if existing else [],
            "message": f"Projeto '{project_id}' tem {len(existing) if existing else 0} agente(s).",
            "questions": [
                {"field": "agent_id", "question": "Qual o ID do novo agente?", "example": "devops", "required": True},
                {"field": "description", "question": "O que este agente faz?", "example": "Gerencia infraestrutura e deploy", "required": True},
                {"field": "agent_type", "question": "Qual o tipo do agente?", "options": ["dev", "qa", "designer", "custom"], "required": True},
            ],
        }
    if agent_id in existing:
        return {"error": f"Agente '{agent_id}' ja existe no projeto '{project_id}'.", "existing_agents": list(existing.keys())}

    contexts_base = Path("contexts") / project_id
    agent_dir = contexts_base / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    actions = DEFAULT_ACTIONS.get(agent_type, DEFAULT_ACTIONS["default"])
    actions_table = "\n".join(f"| {a[0]} | {a[1]} |" for a in actions)
    context_content = CONTEXT_TEMPLATE_WORKER.format(agent_id=agent_id, project_name=project_id, description=description or f"Agente {agent_id}", actions_table=actions_table, working_dir=str(Path.cwd()))
    ctx_file = agent_dir / "CONTEXTO.md"
    ctx_file.write_text(context_content, encoding="utf-8")

    emoji = AGENT_EMOJIS.get(agent_type, "🤖")
    proj_json = contexts_base / "project.json"
    if proj_json.exists():
        data = json.loads(proj_json.read_text(encoding="utf-8"))
        data.setdefault("agents", []).append({"agent_id": agent_id, "module_path": f"src/agents/{project_id}_{agent_id}.py", "class_name": f"{project_id.title().replace('-','')}{agent_id.title().replace('-','')}", "context_limit_kb": 10.0, "llm_provider": "auto", "emoji": emoji, "description": description or ""})
        proj_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "step": "complete", "status": "created",
        "agent": {"agent_id": agent_id, "project_id": project_id, "type": agent_type, "emoji": emoji},
        "context_file": str(ctx_file),
        "next_steps": ["Implemente a classe Python do agente", f"Module path sugerido: src/agents/{project_id}_{agent_id}.py", "Reinicie o Agent Factory para carregar o novo agente"],
    }


# ── Resources ────────────────────────────────────────────────────────────────


@mcp.resource("afp://{project_id}/events")
def events_resource(project_id: str) -> list[dict[str, Any]]:
    """Eventos recentes de um projeto."""
    return read_events(project_id, limit=100)


@mcp.resource("afp://{project_id}/agents")
def agents_resource(project_id: str) -> dict[str, Any]:
    """Lista de agentes de um projeto com referencias."""
    registry = _get_registry()
    refs = registry.list_agent_refs(project_id)
    return {
        "project_id": project_id,
        "agents": {
            aid: {
                "agent_id": ref.agent_id,
                "class_name": ref.class_name,
                "context_file": ref.context_file,
                "context_limit_kb": ref.context_limit_kb,
            }
            for aid, ref in refs.items()
        },
    }


@mcp.resource("afp://{project_id}/{agent_id}/context")
def context_resource(project_id: str, agent_id: str) -> str:
    """Arquivo de contexto de um agente."""
    registry = _get_registry()
    ref = registry.get_agent_ref(project_id, agent_id)
    if not ref or not ref.context_file:
        return f"# {agent_id}\n\nNo context file configured."
    ctx_path = Path(ref.context_file)
    if ctx_path.exists():
        return ctx_path.read_text(encoding="utf-8")
    return f"# {agent_id}\n\nContext file not found: {ref.context_file}"


@mcp.resource("afp://{project_id}/{agent_id}/capabilities")
def capabilities_resource(project_id: str, agent_id: str) -> dict[str, Any]:
    """Capacidades de um agente."""
    registry = _get_registry()
    try:
        agent = registry.load_agent(project_id, agent_id)
        return agent.get_capabilities()
    except Exception as e:
        return {"error": str(e)}


# ── Entrypoints ──────────────────────────────────────────────────────────────


def run_stdio():
    """Inicia servidor MCP via stdio (para integracao com OpenCode)."""
    import asyncio
    asyncio.run(mcp.run_stdio_async())


def run_sse(host: str = "127.0.0.1", port: int = 8081):
    """Inicia servidor MCP via SSE (para debug / HTTP)."""
    import asyncio
    mcp.settings.host = host
    mcp.settings.port = port
    asyncio.run(mcp.run_sse_async())


if __name__ == "__main__":
    import sys
    if "--sse" in sys.argv:
        run_sse()
    else:
        run_stdio()
