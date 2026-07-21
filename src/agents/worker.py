"""Worker declarativo: carrega acoes e identidade de configuracao JSON."""

import json
from pathlib import Path
from typing import Any, Optional

from src.sdk.base import StandardBaseAgent
from src.sdk.factory import AgentFactory, AgentDef
from src.protocols.schema import AgentRole, TaskOutput


class DeclarativeWorker(StandardBaseAgent):
    """Worker generico que carrega sua configuracao de um JSON declarativo.

    O JSON segue o schema AgentDef e e resolvido pelo agent_id:
    busca em src/agents/configs/{agent_id}.json.

    Acoes com handler Python usam o handler registrado via AgentFactory.
    Acoes sem handler usam _llm_fallback com LLM proprio.
    """

    _DEFAULT_LLM = "auto"

    def __init__(self, project_id: str, notifier, context_file: Optional[str] = None,
                 context_limit_kb: Optional[float] = None, **kwargs):
        agent_id = self._resolve_agent_id(context_file, kwargs)
        role = kwargs.pop("role", AgentRole.WORKER)

        super().__init__(
            agent_id=agent_id,
            project_id=project_id,
            notifier=notifier,
            role=role,
            context_file=context_file,
            context_limit_kb=context_limit_kb or 15.0,
        )
        self._agent_factory_instance = None
        config = self._load_config(agent_id)
        self._config = config or {}
        if config:
            try:
                agent_def = AgentDef(**config)
                self._agent_factory_instance = AgentFactory.build(agent_def, project_id, notifier)
            except Exception:
                pass

    @staticmethod
    def _resolve_agent_id(context_file: Optional[str], kwargs: dict) -> str:
        aid = kwargs.pop("agent_id", None)
        if aid:
            return aid
        if context_file:
            p = Path(context_file)
            name = p.parent.name
            if name:
                return name
        return "worker"

    def _load_config(self, agent_id: str) -> Optional[dict]:
        config_dir = Path(__file__).parent / "configs"
        config_file = config_dir / f"{agent_id}.json"
        if config_file.exists():
            try:
                return json.loads(config_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def execute(self, task: dict[str, Any]) -> TaskOutput:
        if self._agent_factory_instance is not None:
            try:
                result = self._agent_factory_instance.execute(task)
                if isinstance(result, TaskOutput):
                    return result
                return TaskOutput.from_execute_output(result)
            except Exception:
                pass
        from src.sdk.factory import AgentFactory as AF
        return AF._llm_fallback(task, self, AgentDef(id=self.agent_id, actions=self._config.get("actions", {})))
