"""
Agent Factory — Agent Loader
=============================
Carrega agentes sob demanda a partir de referências.

Princípio: Agent Factory é plataforma de execução, não repositório de agentes.
Cada projeto mantém seus agentes. Factory apenas referencia e executa.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional, Type

from .agents.base import AgentBase
from .protocols.events import EventNotifier


class AgentReference:
    """
    Referência a um agente em projeto externo.
    
    Attributes:
        agent_id: ID único do agente
        module_path: Caminho para o módulo Python (diretório ou arquivo)
        class_name: Nome da classe do agente
        context_file: Caminho opcional para arquivo de contexto
        context_limit_kb: Limite de contexto em KB
    """
    
    def __init__(
        self,
        agent_id: str,
        module_path: str,
        class_name: str,
        context_file: Optional[str] = None,
        context_limit_kb: float = 15.0,
    ):
        self.agent_id = agent_id
        self.module_path = Path(module_path)
        self.class_name = class_name
        self.context_file = context_file
        self.context_limit_kb = context_limit_kb
    
    def to_dict(self) -> dict:
        """Serializa para dict."""
        return {
            "agent_id": self.agent_id,
            "module_path": str(self.module_path),
            "class_name": self.class_name,
            "context_file": self.context_file,
            "context_limit_kb": self.context_limit_kb,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentReference":
        """Deserializa de dict."""
        return cls(
            agent_id=data["agent_id"],
            module_path=data["module_path"],
            class_name=data["class_name"],
            context_file=data.get("context_file"),
            context_limit_kb=data.get("context_limit_kb", 15.0),
        )


class AgentLoader:
    """
    Carrega agentes sob demanda a partir de referências.
    
    Uso:
        loader = AgentLoader()
        
        # Criar referência
        ref = AgentReference(
            agent_id="renderizacao",
            module_path="C:/Users/rafae/PersonalTrainerAgent/agentes/renderizacao",
            class_name="RenderizacaoAgent",
        )
        
        # Carregar agente (sob demanda)
        agent = loader.load(ref, project_id="pta", notifier=notifier)
        
        # Executar
        result = agent.run({"task_id": "render-01", "action": "render"})
    """
    
    def __init__(self):
        self._loaded_modules: dict[str, Any] = {}
    
    def load(
        self,
        reference: AgentReference,
        project_id: str,
        notifier: EventNotifier,
    ) -> AgentBase:
        """
        Carrega agente a partir de referência.
        
        Args:
            reference: Referência ao agente
            project_id: ID do projeto
            notifier: Notifier do projeto
            
        Returns:
            Instância do agente
            
        Raises:
            ImportError: Se o módulo não for encontrado
            AttributeError: Se a classe não existir no módulo
            ValueError: Se a classe não herdar de AgentBase
        """
        # Verificar se o módulo já foi carregado
        cache_key = f"{reference.module_path}:{reference.class_name}"
        
        if cache_key not in self._loaded_modules:
            self._loaded_modules[cache_key] = self._import_module(reference)
        
        module = self._loaded_modules[cache_key]
        
        # Obter classe
        if not hasattr(module, reference.class_name):
            raise AttributeError(
                f"Classe '{reference.class_name}' não encontrada em {reference.module_path}"
            )
        
        agent_class = getattr(module, reference.class_name)
        
        # Validar herança
        if not (isinstance(agent_class, type) and issubclass(agent_class, AgentBase)):
            raise ValueError(
                f"Classe '{reference.class_name}' não herda de AgentBase"
            )
        
        # Instanciar com context tracking
        kwargs = {
            "project_id": project_id,
            "notifier": notifier,
        }
        
        if reference.context_file:
            kwargs["context_file"] = reference.context_file
        
        if reference.context_limit_kb:
            kwargs["context_limit_kb"] = reference.context_limit_kb
        
        return agent_class(**kwargs)
    
    def _import_module(self, reference: AgentReference) -> Any:
        """Importa módulo dinamicamente."""
        module_path = reference.module_path
        
        # Determinar caminho do arquivo __init__.py
        if module_path.is_dir():
            init_file = module_path / "__init__.py"
        else:
            init_file = module_path
        
        if not init_file.exists():
            raise ImportError(
                f"Módulo não encontrado: {init_file}"
            )
        
        # Import dinâmico
        spec = importlib.util.spec_from_file_location(
            reference.class_name,
            str(init_file),
        )
        
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Não foi possível carregar spec de {init_file}"
            )
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[reference.class_name] = module
        spec.loader.exec_module(module)
        
        return module
    
    def clear_cache(self):
        """Limpa cache de módulos carregados."""
        self._loaded_modules.clear()
    
    def reload(self, reference: AgentReference) -> Any:
        """Recarrega módulo (limpa cache e recarrega)."""
        cache_key = f"{reference.module_path}:{reference.class_name}"
        if cache_key in self._loaded_modules:
            del self._loaded_modules[cache_key]
        
        return self._import_module(reference)


# Instância global do loader
_global_loader: Optional[AgentLoader] = None


def get_loader() -> AgentLoader:
    """Retorna instância global do loader."""
    global _global_loader
    if _global_loader is None:
        _global_loader = AgentLoader()
    return _global_loader
