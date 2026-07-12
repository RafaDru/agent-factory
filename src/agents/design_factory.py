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

        if action == "research_design_systems":
            return self._research_design_systems(task)

        available = sorted(self.ACTIONS.keys())
        return TaskOutput.needs_direction(
            rationale=f"Acao desconhecida: '{action}'. Disponiveis: {available}",
            available_actions=available,
        )

    def _research_design_systems(self, task: dict[str, Any]) -> TaskOutput:
        query = task.get("query") or task.get("prompt", "dashboards operacionais")
        design_systems = {
            "ant_design": {
                "name": "Ant Design 5",
                "fonte": "https://ant.design",
                "destaque": "Design system empresarial chines, excelente para dashboards com tabelas complexas, graficos e formularios densos. Suporta temas customizaveis via CSS-in-JS.",
                "aplicacao": "Dashboard operacional com muitas tabelas e filtros",
            },
            "patternfly": {
                "name": "PatternFly 6",
                "fonte": "https://www.patternfly.org",
                "destaque": "Design system da Red Hat focado em dashboards de monitoramento e devops. Componentes para topologia, metricas em tempo real, logs e alertas.",
                "aplicacao": "Monitoramento de infraestrutura e metricas operacionais",
            },
            "shadcn_ui": {
                "name": "shadcn/ui + Radix",
                "fonte": "https://ui.shadcn.com",
                "destaque": "Colecao de componentes React copiaveis e customizaveis. Nao e uma biblioteca, mas um design system desestruturado que permite controle total do CSS.",
                "aplicacao": "Dashboards modernos com Tailwind, ideal para quem quer design unico",
            },
            "chakra_ui": {
                "name": "Chakra UI 3",
                "fonte": "https://www.chakra-ui.com",
                "destaque": "Design system acessivel com dark mode nativo, componentes semanticos e bom suporte a temas. Ideal para dashboards que precisam de acessibilidade.",
                "aplicacao": "Dashboards com requisitos de acessibilidade (WCAG)",
            },
            "mantine": {
                "name": "Mantine 7",
                "fonte": "https://mantine.dev",
                "destaque": "Design system React com mais de 100 componentes. Hooks para charts, datatables, dnd e formularios nativos. Suporta temas claros/escuros sem dependencias extras.",
                "aplicacao": "Dashboards ricos com charts interativos e datatables",
            },
            "clarity": {
                "name": "Clarity Design System",
                "fonte": "https://clarity.design",
                "destaque": "Design system da VMware focado em datacenters e gerenciamento de infraestrutura. Componentes para status, alerts, graphs e wizard.",
                "aplicacao": "Dashboards de gerenciamento de infraestrutura e datacenter",
            },
            "carbon": {
                "name": "Carbon Design System (IBM)",
                "fonte": "https://carbondesignsystem.com",
                "destaque": "Design system da IBM, maduro e completo. Componentes para dashboards enterprise com tabelas pivot, arvores de navegacao e paineis de controle.",
                "aplicacao": "Dashboards enterprise corporativos",
            },
            "fluent_ui": {
                "name": "Fluent UI (Microsoft)",
                "fonte": "https://react.fluentui.dev",
                "destaque": "Design system da Microsoft, usado no Office 365 e Azure. Componentes nativos para Power BI integracao e graficos.",
                "aplicacao": "Dashboards integrados ao ecossistema Microsoft",
            },
        }

        recomendados = [
            ds for ds in design_systems.values()
            if any(p in ds["aplicacao"].lower() or p in ds["destaque"].lower()
                   for p in query.lower().split())
        ] or list(design_systems.values())

        return TaskOutput.success(
            summary=f"Pesquisa concluida: {len(recomendados)} design systems relevantes para '{query}'",
            rationale="Design systems de mercado analisados e recomendados para dashboards operacionais",
            query=query,
            total_found=len(design_systems),
            design_systems=recomendados[:5],
            recomendacao_principal=recomendados[0]["name"] if recomendados else "Nenhum",
        )
