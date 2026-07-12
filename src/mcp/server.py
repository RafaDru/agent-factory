from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.registry import get_registry
from src.protocols.schema import AgentStatus

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
    subordinates = {}
    refs = registry.list_agent_refs(project_id)
    for aid in refs:
        if aid == "coordenador":
            continue
        try:
            subordinate = registry.load_agent(project_id, aid)
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

    O agente e carregado sob demanda, executa a tarefa e retorna o resultado.
    Em caso de erro, retorna um StructuredError com `error_type`, 
    `available_actions`, `doc_path` e `hint` para correcao.

    Args:
        project_id: ID do projeto (ex: "afp", "pta")
        agent_id: ID do agente (ex: "dev", "qa", "coordenador")
        task: Dicionario com a tarefa. Deve conter no minimo "action" e
              os parametros especificos da acao.

    Returns:
        Resultado da execucao com status, output e metricas.
    """
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

    # Auto-wire subordinates if this is a coordinator
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


@mcp.tool()
def run_objective(
    project_id: str,
    objective: str,
    context: str = "",
) -> dict[str, Any]:
    """Envia um objetivo de alto nivel para o coordenador do projeto.

    O coordenador carrega seu contexto, planeja a execucao (DAG de tarefas)
    e delega para os workers apropriados. O resultado agrega todas as saidas.

    Args:
        project_id: ID do projeto (ex: "afp")
        objective: Descricao do objetivo em linguagem natural
        context: Contexto adicional ou restricoes para a execucao

    Returns:
        Resultado consolidado com plano, execucoes individuais e status final.
    """
    registry = _get_registry()

    try:
        agent = registry.load_agent(project_id, "coordenador")
    except ValueError as e:
        return {
            "error_type": "coordinator_not_found",
            "message": str(e),
            "project_id": project_id,
        }

    _wire_subordinates(registry, project_id, agent)

    task = {
        "task_id": f"obj-{abs(hash(objective)) % 10000:04d}",
        "action": "plan_and_execute",
        "goal": objective,
        "context": context,
    }

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
