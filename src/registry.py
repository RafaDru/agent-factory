"""
Agent Factory — Project Registry
==================================
Registo centralizado de projetos com segregação completa.
Cada projeto tem seus próprios agentes, configs e eventos.

Princípio: Agent Factory é plataforma de execução, não repositório de agentes.
Agentes vivem nos projetos. Factory apenas referencia e executa sob demanda.
"""

import json
from pathlib import Path
from typing import Any, Optional
from src.protocols.schema import ProjectConfig, AgentEvent, AgentStatus
from src.protocols.events import EventNotifier
from src.loader import AgentReference, AgentLoader, get_loader


class ProjectRegistry:
    """
    Registro centralizado de projetos.
    
    Gerencia múltiplos projetos com segregação completa.
    Cada projeto tem:
    - Configuração própria
    - Referências a agentes (não instâncias)
    - Eventos próprios
    - Dashboard próprio (via project_id)
    
    Uso:
        registry = ProjectRegistry()
        
        # Registrar projeto PTA
        registry.register(ProjectConfig(
            project_id="pta",
            name="Personal Trainer Agent",
        ))
        
        # Adicionar referência de agente
        registry.add_agent_ref("pta", AgentReference(
            agent_id="renderizacao",
            module_path="C:/Users/rafae/PersonalTrainerAgent/agentes/renderizacao",
            class_name="RenderizacaoAgent",
        ))
        
        # Carregar e executar agente (sob demanda)
        agent = registry.load_agent("pta", "renderizacao")
        result = agent.run({"task_id": "render-01", "action": "render"})
    """
    
    def __init__(self, base_dir: str = ".agent-factory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._projects: dict[str, ProjectConfig] = {}
        self._notifiers: dict[str, EventNotifier] = {}
        self._agent_refs: dict[str, dict[str, AgentReference]] = {}  # project_id -> {agent_id -> ref}
        
        # Carregar projetos existentes
        self._load_projects()
        self._load_agent_refs()
    
    def register(self, config: ProjectConfig) -> str:
        """
        Registra um novo projeto.
        
        Args:
            config: Configuração do projeto
            
        Returns:
            project_id registrado
        """
        self._projects[config.project_id] = config
        
        # Criar notifier para o projeto
        self._notifiers[config.project_id] = EventNotifier(
            config.project_id,
            output_dir=str(self.base_dir / "events")
        )
        
        # Inicializar mapa de agentes
        if config.project_id not in self._agent_refs:
            self._agent_refs[config.project_id] = {}
        
        # Salvar configuração
        self._save_project(config)
        
        return config.project_id
    
    def unregister(self, project_id: str):
        """Remove um projeto do registro."""
        if project_id in self._projects:
            del self._projects[project_id]
        if project_id in self._notifiers:
            del self._notifiers[project_id]
        if project_id in self._agent_refs:
            del self._agent_refs[project_id]
        
        # Remover arquivos do projeto
        project_dir = self.base_dir / "events" / project_id
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
    
    def add_agent_ref(self, project_id: str, ref: AgentReference):
        """
        Adiciona referência de agente a um projeto.
        
        Args:
            project_id: ID do projeto
            ref: Referência ao agente
        """
        if project_id not in self._agent_refs:
            self._agent_refs[project_id] = {}
        
        self._agent_refs[project_id][ref.agent_id] = ref
        self._save_agent_refs(project_id)
    
    def get_agent_ref(self, project_id: str, agent_id: str) -> Optional[AgentReference]:
        """Retorna referência de um agente."""
        refs = self._agent_refs.get(project_id, {})
        return refs.get(agent_id)
    
    def list_agent_refs(self, project_id: str) -> dict[str, AgentReference]:
        """Lista todas as referências de agentes de um projeto."""
        return self._agent_refs.get(project_id, {})
    
    def load_agent(self, project_id: str, agent_id: str):
        """
        Carrega agente sob demanda.
        
        Args:
            project_id: ID do projeto
            agent_id: ID do agente
            
        Returns:
            Instância do agente
            
        Raises:
            ValueError: Se o agente não existir
        """
        ref = self.get_agent_ref(project_id, agent_id)
        if not ref:
            raise ValueError(f"Agent '{agent_id}' not found in project '{project_id}'")
        
        notifier = self.get_notifier(project_id)
        if not notifier:
            raise ValueError(f"Notifier not found for project '{project_id}'")
        
        loader = get_loader()
        return loader.load(ref, project_id, notifier)
    
    def get_config(self, project_id: str) -> Optional[ProjectConfig]:
        """Retorna configuração de um projeto."""
        return self._projects.get(project_id)
    
    def get_notifier(self, project_id: str) -> Optional[EventNotifier]:
        """Retorna notifier de um projeto."""
        return self._notifiers.get(project_id)
    
    def list_projects(self) -> list[ProjectConfig]:
        """Lista todos os projetos registrados."""
        return list(self._projects.values())
    
    def list_project_ids(self) -> list[str]:
        """Lista IDs de todos os projetos."""
        return list(self._projects.keys())
    
    def project_exists(self, project_id: str) -> bool:
        """Verifica se um projeto existe."""
        return project_id in self._projects
    
    def get_project_status(self, project_id: str) -> dict[str, Any]:
        """Retorna status consolidado de um projeto."""
        notifier = self.get_notifier(project_id)
        if not notifier:
            return {"error": "Project not found"}
        
        status = notifier.get_status()
        events = notifier.get_events()
        
        # Contar agentes
        agents = set()
        completed = 0
        failed = 0
        
        for event in events:
            agents.add(event.agent_id)
            if event.status == AgentStatus.COMPLETED:
                completed += 1
            elif event.status == AgentStatus.FAILED:
                failed += 1
        
        return {
            "project_id": project_id,
            "config": self._projects.get(project_id, {}),
            "status": status,
            "agents": list(agents),
            "agent_refs": list(self.list_agent_refs(project_id).keys()),
            "total_events": len(events),
            "completed_events": completed,
            "failed_events": failed,
        }
    
    def get_all_status(self) -> dict[str, dict]:
        """Retorna status de todos os projetos."""
        return {
            pid: self.get_project_status(pid)
            for pid in self._projects
        }
    
    def _save_project(self, config: ProjectConfig):
        """Salva configuração do projeto em disco."""
        project_dir = self.base_dir / "projects" / config.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = project_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(mode="json"), f, indent=2, default=str)
    
    def _save_agent_refs(self, project_id: str):
        """Salva referências de agentes em disco."""
        refs = self._agent_refs.get(project_id, {})
        if not refs:
            return
        
        project_dir = self.base_dir / "projects" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        refs_file = project_dir / "agents.json"
        refs_data = {aid: ref.to_dict() for aid, ref in refs.items()}
        
        with open(refs_file, "w", encoding="utf-8") as f:
            json.dump(refs_data, f, indent=2, default=str)
    
    def _load_projects(self):
        """Carrega projetos existentes do disco."""
        projects_dir = self.base_dir / "projects"
        if not projects_dir.exists():
            return
        
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                config_file = project_dir / "config.json"
                if config_file.exists():
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        config = ProjectConfig(**data)
                        self._projects[config.project_id] = config
                        self._notifiers[config.project_id] = EventNotifier(
                            config.project_id,
                            output_dir=str(self.base_dir / "events")
                        )
                        self._agent_refs[config.project_id] = {}
                    except Exception as e:
                        print(f"Error loading project {project_dir.name}: {e}")
    
    def _load_agent_refs(self):
        """Carrega referências de agentes do disco."""
        projects_dir = self.base_dir / "projects"
        if not projects_dir.exists():
            return
        
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                refs_file = project_dir / "agents.json"
                if refs_file.exists():
                    try:
                        project_id = project_dir.name
                        with open(refs_file, "r", encoding="utf-8") as f:
                            refs_data = json.load(f)
                        
                        self._agent_refs[project_id] = {}
                        for aid, ref_dict in refs_data.items():
                            self._agent_refs[project_id][aid] = AgentReference.from_dict(ref_dict)
                    except Exception as e:
                        print(f"Error loading agent refs for {project_dir.name}: {e}")


# Instância global do registry
_global_registry: Optional[ProjectRegistry] = None


def get_registry(base_dir: str = ".agent-factory") -> ProjectRegistry:
    """Retorna a instância global do registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ProjectRegistry(base_dir)
    return _global_registry


def register_project(config: ProjectConfig) -> str:
    """Shortcut para registrar um projeto."""
    return get_registry().register(config)


def get_project_notifier(project_id: str) -> Optional[EventNotifier]:
    """Shortcut para obter notifier de um projeto."""
    return get_registry().get_notifier(project_id)
