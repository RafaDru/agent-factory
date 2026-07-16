"""Agente Arquiteto — revisao arquitetural e governanca tecnica."""
from pathlib import Path
from typing import Any
from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput


class ArchitectAgent(StandardBaseAgent):
    """Agente de Arquitetura para revisao e governanca tecnica do AFP."""

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "review_architecture": {
            "description": "Revisa consistencia arquitetural de um arquivo ou diretorio",
            "params": {"path": "str - caminho do arquivo ou diretorio"},
        },
        "analyze_project": {
            "description": "Analisa estrutura do projeto e sugere melhorias",
            "params": {"path": "str - diretorio raiz para analise"},
        },
        "suggest_fixes": {
            "description": "Sugere correcoes arquiteturais para um arquivo",
            "params": {"file_path": "str - caminho do arquivo", "error": "str - descricao do erro"},
        },
        "get_capabilities": {
            "description": "Retorna as acoes disponiveis neste agente",
            "params": {},
        },
    }

    def __init__(self, agent_id: str, project_id: str, **kwargs):
        super().__init__(
            agent_id=agent_id,
            project_id=project_id,
            role=AgentRole.ARCHITECT,
            context_file=Path("contexts") / project_id / agent_id / "CONTEXTO.md",
            **kwargs,
        )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "")
        if action == "get_capabilities":
            return {"actions": list(self.ACTIONS.keys())}

        if not self._llm:
            return {"status": "error", "error": "Nenhum LLM provider disponivel"}

        goal = task.get("goal", task.get("error", task.get("path", task.get("file_path", ""))))
        focus = task.get("focus", "arquitetura")

        prompt = f"""Voce e um arquiteto de software revisando o projeto Agent Factory Platform.

Foco: {focus}
Tarefa: {goal}

Contexto completo do agente:
{task.get('_context_tree_domains', '')}

Responda com analise tecnica detalhada, apontando:
1. Problemas arquiteturais encontrados
2. Sugestoes de melhoria com prioridade
3. Padroes que devem ser seguidos
4. Riscos identificados
"""

        messages = [
            {"role": "system", "content": "Voce e um arquiteto de software senior. Responda em portugues."},
            {"role": "user", "content": prompt},
        ]
        response = self._llm.chat(messages)
        return {"review": response, "status": "completed"}
