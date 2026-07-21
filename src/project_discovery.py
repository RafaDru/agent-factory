"""
Agent Factory — Project Auto-Discovery
========================================
Escaneia contexts/*/project.json e registra projetos automaticamente.
Elimina a necessidade de codificar projetos em start_agent_factory.py.
"""
import json
from pathlib import Path
from typing import Optional


def _resolve_path(path_str: str) -> str:
    """Resolve ~/ e caminhos relativos."""
    if path_str.startswith("~/"):
        return str(Path.home() / path_str[2:])
    return path_str


def discover_projects(contexts_dir: Path = Path("contexts")) -> list[dict]:
    """Escaneia contexts/*/project.json e retorna lista de projetos.

    Schema: Projeto (1:1) Time (1:N) Agentes.
    Cada project.json define 1 projeto com 1 time e lista de agentes.

    Returns:
        Lista de dicts: {project: {project_id, name, ...}, agent_refs: [{agent_id, module_path, ...}]}
    """
    projects = []
    if not contexts_dir.exists():
        return projects

    for proj_file in sorted(contexts_dir.rglob("project.json")):
        try:
            data = json.loads(proj_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            continue

        project_id = data.get("project_id", "")
        if not project_id:
            continue

        project = {
            "project_id": project_id,
            "name": data.get("project_name", project_id),
            "description": data.get("description", ""),
            "working_dir": _resolve_path(data.get("working_dir", ".")),
            "icon": data.get("icon", "📦"),
            "team_id": data.get("team_id", project_id),
            "team_name": data.get("team_name", data.get("project_name", project_id)),
        }

        agent_refs = []
        for agent_data in data.get("agents", []):
            agent_id = agent_data.get("agent_id", "")
            if not agent_id:
                continue

            module_path = _resolve_path(agent_data.get("module_path", ""))
            class_name = agent_data.get("class_name", "")

            # Context file: contexts/<project_id>/<agent_id>/CONTEXTO.md
            ctx_dir = proj_file.parent
            context_file = ctx_dir / agent_id / "CONTEXTO.md"
            if not context_file.exists():
                context_file = None

            agent_refs.append({
                "agent_id": agent_id,
                "module_path": module_path,
                "class_name": class_name,
                "context_limit_kb": agent_data.get("context_limit_kb", 10.0),
                "context_file": str(context_file) if context_file else None,
                "llm_provider": agent_data.get("llm_provider", "auto"),
                "emoji": agent_data.get("emoji", "🤖"),
                "description": agent_data.get("description", ""),
            })

        projects.append({
            "project": project,
            "agent_refs": agent_refs,
        })

    return projects


def register_discovered_projects(registry, notifier_factory=None):
    """Registra todos os projetos descobertos em contexts/ no registry.

    Schema project.json: Projeto (1:1) Time (1:N) Agentes
    Cada arquivo project.json define 1 projeto com 1 time e N agentes.
    """
    from src.protocols.schema import ProjectConfig
    from src.loader import AgentReference

    discovered = discover_projects()
    registered_count = 0

    for entry in discovered:
        proj = entry["project"]
        project_id = proj["project_id"]

        # Register project if not exists
        if not registry.project_exists(project_id):
            registry.register(ProjectConfig(
                project_id=project_id,
                name=proj["name"],
                description=proj["description"],
            ))
            registered_count += 1
            print(f"  [Discovery] Projeto: {project_id} ({proj['name']})   Time: {proj.get('team_name','?')}")

        # Register / update agent references from project.json
        existing_refs = registry.list_agent_refs(project_id)
        for agent_data in entry.get("agent_refs", []):
            agent_id = agent_data["agent_id"]

            ref = AgentReference(
                agent_id=agent_id,
                module_path=agent_data["module_path"],
                class_name=agent_data["class_name"],
                context_limit_kb=agent_data.get("context_limit_kb", 10.0),
                context_file=agent_data.get("context_file"),
            )

            if agent_id not in existing_refs:
                registry.add_agent_ref(project_id, ref)
                print(f"    + agente: {agent_id} ({agent_data['class_name']})")
            else:
                existing = existing_refs[agent_id]
                if (existing.module_path != ref.module_path or existing.class_name != ref.class_name or
                        existing.context_file != ref.context_file):
                    registry.add_agent_ref(project_id, ref)  # overwrite
                    print(f"    ~ agente: {agent_id} atualizado ({ref.class_name})")

    if registered_count:
        print(f"  [Discovery] {registered_count} novo(s) projeto(s) registrado(s)")
    else:
        print(f"  [Discovery] Projetos ja registrados em contexts/")

    return registered_count
