import json
from typing import Any, Optional
from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput

class DesignAgent(StandardBaseAgent):
    """Agente de Design para evolucao da interface do Dashboard do Agent Factory."""

    ACTIONS = {
        "design_ui": {
            "description": "Cria propostas de UI (CSS/HTML) com foco em dashboards",
            "params": {"prompt": "str - detalhes do design ou mudanca"},
        },
        "prototype": {
            "description": "Gera prototipos HTML/JS/Tailwind",
            "params": {"prompt": "str - funcionalidades solicitadas"},
        },
        "analyze_ux": {
            "description": "Analisa tendencias de UX/UI",
            "params": {"prompt": "str - area de analise (ex: performance dashboard)"},
        },
    }

    def __init__(self, project_id: str, notifier: Any, **kwargs):
        super().__init__(
            agent_id="designer",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
            **kwargs,
        )

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> TaskOutput:
        action = task.get("action")
        prompt = task.get("prompt", "")

        if action == "analyze_ux":
            return TaskOutput.success(
                summary="Analise de UX concluida",
                rationale="Tendencias atuais indicam cards expansiveis, metricas de latencia em tempo real e seletor de tema (Light/Dark) para reduzir fadiga visual.",
                response="Cards expansivos + metricas em tempo real + tema Light/Dark",
            )

        if action in ("design_ui", "prototype"):
            return TaskOutput.success(
                summary=f"Design gerado para: {prompt[:80]}",
                rationale=f"Criado prototipo baseado em: {prompt}",
                action=action, prompt=prompt,
            )

        available = sorted(self.ACTIONS.keys())
        return TaskOutput.needs_direction(
            rationale=f"Acao desconhecida: '{action}'. Disponiveis: {available}",
            available_actions=available,
        )
