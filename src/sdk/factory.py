"""Fabrica Declarativa de Agentes — YAML/JSON -> StandardBaseAgent."""

import importlib
import json
from pathlib import Path
from typing import Any, Optional, get_type_hints

from pydantic import BaseModel, Field

from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput, OutputStatus
from src.protocols.events import EventNotifier
from src.sdk.hooks import HookRegistry, HookPoint, HookContext


class ActionDef(BaseModel):
    """Definicao declarativa de uma acao de agente."""
    description: str = ""
    params: dict[str, str] = Field(default_factory=dict)
    handler: Optional[str] = None       # "modulo.funcao" — Python callable
    llm_prompt: Optional[str] = None    # usado se handler for None (LLM decide)


class AgentDef(BaseModel):
    """Definicao declarativa de um agente."""
    id: str
    role: AgentRole = AgentRole.WORKER
    description: str = ""
    prompt: str = ""                     # injetado como contexto/skill
    actions: dict[str, ActionDef] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    llm_provider: Optional[str] = None   # "groq", "ollama", etc.


class AgentFactory:
    """
    Fabrica que constroi agentes a partir de definicoes declarativas.
    
    Uso:
        config = AgentFactory.parse_yaml("agentes/meu_agente.yaml")
        agente = AgentFactory.build(config, project_id="...", notifier=...)
        agente.run({"action": "minha_acao", "input": "..."})
    """

    @staticmethod
    def parse_yaml(path: str) -> AgentDef:
        """Le arquivo YAML e retorna AgentDef."""
        import yaml
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        return AgentDef(**data)

    @staticmethod
    def parse_json(path: str) -> AgentDef:
        """Le arquivo JSON e retorna AgentDef."""
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
        return AgentDef(**data)

    @staticmethod
    def parse_dict(data: dict) -> AgentDef:
        """Converte dict para AgentDef."""
        return AgentDef(**data)

    @staticmethod
    def build(
        config: AgentDef,
        project_id: str,
        notifier: EventNotifier,
        **kwargs,
    ) -> StandardBaseAgent:
        """
        Constroi agente a partir da configuracao declarativa.
        Registra automaticamente as acoes como metodos do agente.
        """
        # Validar handlers antes de criar a classe
        resolved_handlers: dict[str, Any] = {}
        for action_name, action_def in config.actions.items():
            if action_def.handler:
                resolved_handlers[action_name] = _resolve_handler(action_def.handler)
            else:
                resolved_handlers[action_name] = None  # LLM-based

        # Factory method que cria a classe
        class _DeclarativeAgent(StandardBaseAgent):
            ACTIONS = {
                name: {"description": act.description, "params": act.params}
                for name, act in config.actions.items()
            }

            def __init__(self, *args, **outer_kwargs):
                super().__init__(*args, **outer_kwargs)
                self._agent_def = config
                self._prompt = config.prompt

            def execute(self, task: dict[str, Any]) -> TaskOutput:
                action = task.get("action", "")
                handler_fn = resolved_handlers.get(action)
                if handler_fn is None:
                    return AgentFactory._llm_fallback(task, self, config)
                try:
                    result = handler_fn(self, task)
                    if isinstance(result, TaskOutput):
                        return result
                    if isinstance(result, dict):
                        return TaskOutput.from_execute_output(result)
                    return TaskOutput.success(summary=str(result))
                except Exception as e:
                    return TaskOutput.failure(rationale=str(e))

        instance = _DeclarativeAgent(
            agent_id=config.id,
            project_id=project_id,
            notifier=notifier,
            role=config.role,
            **kwargs,
        )

        # Registrar skills como hooks (TODO: carregar skills externos)
        if config.skills:
            for skill_name in config.skills:
                AgentFactory._inject_skill(instance, skill_name, config)

        return instance

    @staticmethod
    def _llm_fallback(task: dict, agent: StandardBaseAgent, config: AgentDef) -> TaskOutput:
        """Quando o action nao tem handler Python, usa LLM para decidir."""
        action = task.get("action", "")
        action_def = config.actions.get(action)
        if not action_def:
            return TaskOutput.needs_direction(
                rationale=f"Acao '{action}' nao definida no agente '{config.id}'",
                available_actions=list(config.actions.keys()),
            )
        return TaskOutput.failure(
            rationale=f"LLM nao configurado para action '{action}'. "
                       "Defina handler Python ou configure llm_provider.",
            available_actions=list(config.actions.keys()),
        )

    @staticmethod
    def _inject_skill(agent: StandardBaseAgent, skill_name: str, config: AgentDef):
        """Injeta uma skill no agente como hooks + actions (TODO)."""
        pass  # Placeholder para integracao futura de skills


def _resolve_handler(handler_path: str) -> Any:
    """
    Resolve "modulo.funcao" para a funcao Python correspondente.
    A funcao recebe (self, task: dict) -> TaskOutput | dict.
    """
    parts = handler_path.split(".")
    if len(parts) < 2:
        raise ValueError(f"Handler deve ser 'modulo.funcao': {handler_path}")

    module_path = ".".join(parts[:-1])
    func_name = parts[-1]

    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise ValueError(f"Modulo nao encontrado: {module_path} (handler: {handler_path})")

    func = getattr(module, func_name, None)
    if func is None or not callable(func):
        raise ValueError(f"Funcao '{func_name}' nao encontrada ou nao callable em {module_path}")

    return func
