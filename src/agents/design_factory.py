import json
import os
from pathlib import Path
from typing import Any, Optional
from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput


class DesignAgent(StandardBaseAgent):
    """Agente de Design para evolucao da interface do Dashboard do Agent Factory."""

    _DEFAULT_LLM = "auto"

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
        "research_design_systems": {
            "description": "Pesquisa design systems do mercado focados em dashboards operacionais",
            "params": {"query": "str (opcional) - filtro de pesquisa"},
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
        self.working_dir = Path(kwargs.get("working_dir", os.getcwd()))

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> TaskOutput:
        action = task.get("action")
        
        if action == "research_design_systems":
            return self._research_design_systems_with_llm(task)

        # Fallback to simple mock responses for other actions for now
        prompt = task.get("prompt", "")
        if action == "analyze_ux":
            return self._analyze_ux_with_llm(task)

        if action in ("design_ui", "prototype"):
            return self._prototype_with_llm(task)

        available = sorted(self.ACTIONS.keys())
        return TaskOutput.needs_direction(
            rationale=f"Acao desconhecida: '{action}'. Disponiveis: {available}",
            available_actions=available,
        )

    def _build_context_prompt(self, task: dict) -> str:
        """Carrega os 3 niveis de contexto se disponiveis e retorna como prefixo do prompt."""
        parts = []
        ctx_global = self.load_global_context()
        if ctx_global:
            parts.append(f"## Contexto Global do Projeto\n\n{ctx_global}")
        mission_id = task.get("_mission_id", "")
        if mission_id:
            ctx_mission = self.load_mission_context(mission_id)
            if ctx_mission:
                parts.append(f"## Contexto da Missão\n\n{ctx_mission}")
            task_id = task.get("_task_id", "")
            if task_id and self.agent_id:
                ctx_task = self.load_task_context(mission_id, task_id, self.agent_id)
                if ctx_task:
                    parts.append(f"## Contexto desta Tarefa\n\n{ctx_task}")
        dep_ctx = task.get("_dependency_context", "")
        if dep_ctx:
            parts.append(dep_ctx)
        return "\n\n".join(parts)

    def _save_artifact(self, task: dict, name: str, content: str):
        """Salva artefato se a task tiver contexto de missao."""
        mid = task.get("_mission_id", "")
        tid = task.get("_task_id", "")
        if mid and tid:
            self.save_task_artifact(mid, tid, self.agent_id, name, content)

    def _analyze_ux_with_llm(self, task: dict[str, Any]) -> TaskOutput:
        ctx_prefix = self._build_context_prompt(task)
        user_prompt = task.get("prompt", "tendencias para dashboards de monitoramento")
        prompt = f"{ctx_prefix}\n\n{user_prompt}" if ctx_prefix else user_prompt
        system_prompt = "Você é um especialista em UX/UI. Analise o prompt do usuário e retorne um parágrafo com as principais tendências e recomendações para a área solicitada. Seja direto e prático."
        
        llm_response = self._llm_think(prompt, system_prompt=system_prompt)
        if llm_response:
            self._save_artifact(task, "analise_ux.md", llm_response)
            return TaskOutput.success(
                summary="Análise de UX concluída via LLM",
                rationale=llm_response,
            )
        return TaskOutput.failure("LLM indisponível para análise de UX.")

    def _prototype_with_llm(self, task: dict[str, Any]) -> TaskOutput:
        ctx_prefix = self._build_context_prompt(task)
        user_prompt = task.get("prompt", "um card de métrica com título, valor e um ícone")
        prompt = f"{ctx_prefix}\n\n{user_prompt}" if ctx_prefix else user_prompt
        system_prompt = "Você é um especialista em UI e Tailwind CSS. Crie um protótipo HTML/Tailwind para o componente solicitado. Retorne APENAS o código HTML."
        
        llm_response = self._llm_think(prompt, system_prompt=system_prompt, max_tokens=4096)
        if llm_response:
            # Simple cleanup to remove markdown fences if the LLM adds them
            code = llm_response.strip()
            if code.startswith("```html"):
                code = code[7:]
            if code.endswith("```"):
                code = code[:-3]
            
            self._save_artifact(task, "prototipo.html", code.strip())
            return TaskOutput.success(
                summary=f"Protótipo gerado para: {user_prompt[:50]}...",
                rationale="Protótipo HTML/Tailwind gerado via LLM.",
                html_code=code.strip(),
            )
        return TaskOutput.failure("LLM indisponível para prototipagem.")

    def _research_design_systems_with_llm(self, task: dict[str, Any]) -> TaskOutput:
        ctx_prefix = self._build_context_prompt(task)
        query = task.get("query") or task.get("prompt", "dashboards operacionais dark mode")

        system_prompt = """Você é um especialista em Design Systems e UX/UI.
Sua tarefa é pesquisar e recomendar os melhores design systems para um determinado caso de uso.
Responda APENAS com um JSON contendo uma chave "design_systems" (uma lista de objetos) e "recomendacao_principal" (o nome do mais recomendado).
Cada objeto na lista deve ter as chaves: "name", "fonte" (URL), "destaque" (um parágrafo), e "aplicacao" (caso de uso ideal).
Seja conciso e direto ao ponto. Analise os prós e contras de cada um para o caso de uso específico."""

        user_prompt = f"Pesquise e recomende os 3 melhores design systems para o seguinte caso de uso: '{query}'. Retorne o resultado no formato JSON especificado."
        prompt = f"{ctx_prefix}\n\n{user_prompt}" if ctx_prefix else user_prompt

        llm_response = self._llm_think(prompt, system_prompt=system_prompt)

        if llm_response:
            try:
                # Naive cleanup of potential markdown fences
                clean_response = llm_response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]

                data = json.loads(clean_response)
                recomendados = data.get("design_systems", [])
                if recomendados:
                    self._save_artifact(task, "design_systems.json", json.dumps(recomendados, ensure_ascii=False, indent=2))
                    return TaskOutput.success(
                        summary=f"LLM Research: {len(recomendados)} design systems encontrados para '{query}'",
                        rationale=f"Pesquisa realizada via LLM ({self._llm.__class__.__name__ if self._llm else 'N/A'}).",
                        query=query,
                        design_systems=recomendados,
                        recomendacao_principal=data.get("recomendacao_principal"),
                    )
            except (json.JSONDecodeError, AttributeError):
                # Se o LLM retornar algo que nao e JSON, cai no fallback
                pass
        
        # Fallback para os dados hardcoded se o LLM falhar ou nao estiver disponivel
        return self._research_design_systems_fallback(task)

    def _research_design_systems_fallback(self, task: dict[str, Any]) -> TaskOutput:
        query = task.get("query") or task.get("prompt", "dashboards operacionais")
        design_systems = {
            "ant_design": {
                "name": "Ant Design 5",
                "fonte": "https://ant.design",
                "destaque": "Componentes ricos para dashboards complexos.",
                "aplicacao": "Dashboard operacional com tabelas e filtros",
            },
            "patternfly": {
                "name": "PatternFly 6",
                "fonte": "https://www.patternfly.org",
                "destaque": "Foco em monitoramento e devops (Red Hat).",
                "aplicacao": "Monitoramento de infraestrutura",
            },
        }

        recomendados = list(design_systems.values())

        return TaskOutput.success(
            summary=f"Fallback Research: {len(recomendados)} design systems para '{query}'",
            rationale="Fallback: Usando dados hardcoded pois o LLM falhou.",
            query=query,
            design_systems=recomendados,
            recomendacao_principal=recomendados[0]["name"],
        )
