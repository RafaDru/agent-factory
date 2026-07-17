"""
Agent Factory — Business Agent (Negocios)
===========================================
Agente de negocios e agilidade: prioriza backlog, valida requisitos,
analisa mercado. Usa LLM para raciocinio autonomo.
"""

import json
from typing import Any

from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput


class BusinessAgent(StandardBaseAgent):
    """Agente de Negocios: backlog, priorizacao, validacao de requisitos."""

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "analisar_mercado": {
            "description": "Pesquisa tendencias e benchmarks de mercado para o projeto",
            "params": {"query": "str (obrigatorio) - area ou nicho para analisar"},
        },
        "definir_prioridades": {
            "description": "Organiza backlog por valor de negocio, retorna lista priorizada",
            "params": {
                "itens": "list (obrigatorio) - lista de itens no backlog",
                "criterios": "str (opcional) - criterios adicionais de priorizacao",
            },
        },
        "validar_requisitos": {
            "description": "Valida se requisitos atendem necessidade de negocio e ROI",
            "params": {
                "requisitos": "str (obrigatorio) - descricao dos requisitos a validar",
                "contexto": "str (opcional) - contexto do projeto ou restricoes",
            },
        },
        "get_capabilities": {
            "description": "Retorna as acoes disponiveis neste agente",
            "params": {},
        },
    }

    def __init__(self, project_id: str, notifier: Any, **kwargs):
        super().__init__(
            agent_id="negocios",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
            **kwargs,
        )

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> TaskOutput:
        action = task.get("action", "")

        if action == "analisar_mercado":
            return self._analisar_mercado(task)
        elif action == "definir_prioridades":
            return self._definir_prioridades(task)
        elif action == "validar_requisitos":
            return self._validar_requisitos(task)
        elif action == "get_capabilities":
            return self._get_capabilities()
        else:
            available = sorted(self.ACTIONS.keys())
            return TaskOutput.needs_direction(
                rationale=f"Acao desconhecida: '{action}'. Disponiveis: {available}",
                available_actions=available,
            )

    def _build_context(self, task: dict) -> str:
        parts = []
        ctx_global = self.load_global_context()
        if ctx_global:
            parts.append(f"## Contexto Global\n\n{ctx_global}")
        mission_id = task.get("_mission_id", "")
        if mission_id:
            ctx = self.load_mission_context(mission_id)
            if ctx:
                parts.append(f"## Contexto da Missao\n\n{ctx}")
        dep = task.get("_dependency_context", "")
        if dep:
            parts.append(dep)
        return "\n\n".join(parts)

    def _analisar_mercado(self, task: dict) -> TaskOutput:
        query = task.get("query") or task.get("prompt", "")
        if not query:
            return TaskOutput.needs_direction(
                rationale="Forneca 'query' para analisar o mercado.",
                available_actions=["get_capabilities"],
            )
        ctx = self._build_context(task)
        prompt = f"{ctx}\n\n## Analise de Mercado\n\n{query}" if ctx else f"## Analise de Mercado\n\n{query}"
        system = (
            "Voce e um analista de negocios experiente em metodologias ageis e produto digital. "
            "Analise o mercado para o contexto solicitado. Retorne: tendencias, benchmarks, "
            "oportunidades e riscos. Seja conciso e objetivo (max 3 paragrafos)."
        )
        response = self._llm_think(prompt, system_prompt=system)
        if response:
            return TaskOutput.success(
                summary=f"Analise de mercado: {query[:60]}...",
                rationale=response,
            )
        return TaskOutput.failure("LLM indisponivel para analise de mercado.")

    def _definir_prioridades(self, task: dict) -> TaskOutput:
        itens = task.get("itens", [])
        if not itens:
            return TaskOutput.needs_direction(
                rationale="Forneca 'itens' (lista) para definir prioridades.",
                available_actions=["get_capabilities"],
            )
        criterios = task.get("criterios", "valor de negocio, urgencia, complexidade")
        ctx = self._build_context(task)
        prompt = (
            f"{ctx}\n\n## Itens do Backlog\n{json.dumps(itens, ensure_ascii=False, indent=2)}"
            f"\n\n## Criterios de Priorizacao\n{criterios}"
        )
        system = (
            "Voce e um Product Owner experiente. Priorize os itens do backlog usando os criterios fornecidos. "
            "Retorne JSON: {\"priorizados\": [{\"item\": \"...\", \"prioridade\": \"alta/media/baixa\", "
            "\"justificativa\": \"...\"}]}"
        )
        response = self._llm_think(f"{prompt}\n\nRetorne JSON priorizado.", system_prompt=system)
        if response:
            try:
                data = json.loads(response.strip().removeprefix("```json").removesuffix("```"))
                return TaskOutput.success(
                    summary=f"{len(data.get('priorizados', []))} itens priorizados",
                    rationale=response,
                    prioridades=data.get("priorizados", []),
                )
            except (json.JSONDecodeError, AttributeError):
                return TaskOutput.success(
                    summary=f"{len(itens)} itens analisados",
                    rationale=response,
                )
        return TaskOutput.failure("LLM indisponivel para priorizacao.")

    def _validar_requisitos(self, task: dict) -> TaskOutput:
        requisitos = task.get("requisitos", "")
        if not requisitos:
            return TaskOutput.needs_direction(
                rationale="Forneca 'requisitos' para validar.",
                available_actions=["get_capabilities"],
            )
        contexto = task.get("contexto", "")
        ctx = self._build_context(task)
        prompt = (
            f"{ctx}\n\n## Requisitos\n{requisitos}"
            f"\n\n## Contexto do Projeto\n{contexto}" if contexto else
            f"{ctx}\n\n## Requisitos\n{requisitos}"
        )
        system = (
            "Voce e um analista de requisitos experiente. Valide os requisitos fornecidos "
            "considerando: clareza, completude, consistencia, testabilidade e valor de negocio. "
            "Retorne JSON: {\"valido\": bool, \"pontos_fortes\": [...], \"melhorias\": [...], "
            "\"riscos\": [...], \"nota\": 1-10}"
        )
        response = self._llm_think(f"{prompt}\n\nRetorne JSON com a validacao.", system_prompt=system)
        if response:
            try:
                data = json.loads(response.strip().removeprefix("```json").removesuffix("```"))
                return TaskOutput.success(
                    summary=f"Requisitos validados: nota {data.get('nota', '?')}/10",
                    rationale=response,
                    validacao=data,
                )
            except (json.JSONDecodeError, AttributeError):
                return TaskOutput.success(
                    summary="Requisitos validados",
                    rationale=response,
                )
        return TaskOutput.failure("LLM indisponivel para validacao.")

    def _get_capabilities(self) -> TaskOutput:
        return TaskOutput.success(
            summary="BusinessAgent pronto",
            rationale="Acoes de negocios disponiveis",
            actions=self.ACTIONS,
        )
