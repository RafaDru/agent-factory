"""
Agent Factory — Coordenador do Projeto agent-factory-dev (REAL)
===============================================================
Orquestra agentes-factory-dev e qa para evoluir a plataforma.
"""

import sys
from pathlib import Path
from typing import Any, Optional

from src.agents.base import AgentBase, AgentRole, StructuredError
from src.protocols.events import EventNotifier
from src.protocols.schema import AgentEvent, AgentStatus


class AgentFactoryCoordinator(AgentBase):
    """
    Coordenador do projeto agent-factory-dev.
    Delega tarefas para agent-factory-dev e qa, consolida resultados.
    """

    ACTIONS = {
        "delegate": {
            "description": "Delega tarefa para agente-factory-dev ou qa e retorna resultado",
            "params": {
                "agent_id": "str (obrigatorio) - agent-factory-dev | qa",
                "task": "dict (obrigatorio) - {action, ...}",
            },
        },
        "plan_and_execute": {
            "description": "Planeja execucao: coordinator analisa, agent-factory-dev implementa, qa valida",
            "params": {
                "goal": "str (obrigatorio) - descricao do objetivo",
                "tasks": "list[dict] (obrigatorio) - [{agent_id, task, depends_on}...]",
            },
        },
        "get_capabilities": {
            "description": "Retorna as acoes disponiveis neste agente",
            "params": {},
        },
    }

    def __init__(
        self,
        project_id: str,
        notifier: EventNotifier,
        agents: Optional[dict[str, AgentBase]] = None,
        **kwargs,
    ):
        super().__init__(
            agent_id="coordenador",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.COORDINATOR,
            context_limit_kb=kwargs.get("context_limit_kb", 15.0),
            context_file=kwargs.get("context_file"),
        )
        self.subordinates: dict[str, AgentBase] = agents or {}

    def set_subordinates(self, agents: dict[str, AgentBase]):
        self.subordinates = agents

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]

        if action == "delegate":
            return self._delegate(task)
        elif action == "plan_and_execute":
            return self._plan_and_execute(task)
        elif action == "get_capabilities":
            return self._get_capabilities()
        else:
            available = sorted(self.ACTIONS.keys())
            raise StructuredError(
                message=f"Acao desconhecida: '{action}'. Acoes disponiveis: {', '.join(available)}",
                error_type="unknown_action",
                action_requested=action,
                available_actions=available,
                doc_path=self.get_doc_path(),
                hint=f"Use action=get_capabilities ou action=delegate para delegar tarefas.",
            )

    def _delegate(self, task: dict) -> dict:
        agent_id = task.get("agent_id", "")
        subtask = task.get("task", {})

        if agent_id not in self.subordinates:
            available = list(self.subordinates.keys())
            return {
                "status": "error",
                "error": f"Subordinado '{agent_id}' nao encontrado. Disponiveis: {available}",
            }

        self.notifier.emit(AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=AgentStatus.RUNNING,
            task_id=subtask.get("task_id", "n/a"),
            project_id=self.project_id,
            message=f"Delegando tarefa '{subtask.get('action', '?')}' para {agent_id}",
        ))

        try:
            result = self.subordinates[agent_id].run(subtask)
            return {
                "status": "ok",
                "agent_id": agent_id,
                "action": subtask.get("action"),
                "result": result.output if hasattr(result, "output") else result,
                "task_status": result.status.value if hasattr(result, "status") else "unknown",
            }
        except Exception as e:
            return {"status": "error", "agent_id": agent_id, "error": str(e)}

    def _plan_and_execute(self, task: dict) -> dict:
        goal = task.get("goal", "")
        tasks = task.get("tasks", [])

        self.notifier.emit(AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=AgentStatus.RUNNING,
            task_id="plan",
            project_id=self.project_id,
            message=f"Executando plano: {goal[:120]}",
        ))

        results = []
        completed_ids = set()

        for step in tasks:
            agent_id = step.get("agent_id", "")
            subtask = step.get("task", {})
            depends_on = step.get("depends_on", [])

            missing = [d for d in depends_on if d not in completed_ids]
            if missing:
                results.append({
                    "step": step.get("name", "?"),
                    "agent_id": agent_id,
                    "status": "skipped",
                    "reason": f"Dependencias nao concluidas: {missing}",
                })
                continue

            self.notifier.emit(AgentEvent(
                agent_id=self.agent_id,
                agent_role=self.role,
                status=AgentStatus.RUNNING,
                task_id=subtask.get("task_id", step.get("name", "?")),
                project_id=self.project_id,
                message=f"Passo '{step.get('name', '?')}' -> {agent_id}",
            ))

            try:
                result = self.subordinates[agent_id].run(subtask)
                results.append({
                    "step": step.get("name", "?"),
                    "agent_id": agent_id,
                    "status": "ok",
                    "result": result.output if hasattr(result, "output") else str(result),
                })
                completed_ids.add(step.get("name"))
            except Exception as e:
                results.append({
                    "step": step.get("name", "?"),
                    "agent_id": agent_id,
                    "status": "error",
                    "error": str(e),
                })

        total = len(tasks)
        ok = sum(1 for r in results if r["status"] == "ok")
        failed = sum(1 for r in results if r["status"] == "error")

        return {
            "status": "ok" if failed == 0 else "partial",
            "goal": goal,
            "total_steps": total,
            "completed": ok,
            "failed": failed,
            "skipped": total - ok - failed,
            "steps": results,
        }

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "subordinates": list(self.subordinates.keys()),
            "actions": self.ACTIONS,
        }
