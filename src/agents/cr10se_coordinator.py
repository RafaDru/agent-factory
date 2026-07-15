"""
Agent Factory — CR-10 SE Coordinator
======================================
Orquestrador do time 3D. Recebe objetivos, gera planos via LLM,
delega tarefas para firmware, visao-llm e gcode-opt e coleta resultados.
"""

from typing import Any, Optional
from pathlib import Path
import time

from src.agents.base import AgentBase, StructuredError
from src.protocols.schema import AgentRole, AgentStatus
from src.protocols.events import EventNotifier


class CR10SECoordinator(AgentBase):
    """
    Coordenador do projeto cr10se.
    Planeja, delega, executa e consolida resultados.
    """

    def __init__(
        self,
        project_id: str,
        notifier: EventNotifier,
        working_dir: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            agent_id="coordenador",
            project_id=project_id,
            notifier=notifier,
            role=kwargs.get("role", AgentRole.COORDINATOR),
            context_limit_kb=kwargs.get("context_limit_kb", 15.0),
            context_file=kwargs.get("context_file"),
        )
        self.working_dir = Path(working_dir or r"C:\Users\rafae\Documents\Impressão 3D")
        self._registry = kwargs.get("registry")

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
        raise StructuredError(
            message=f"Acao desconhecida: '{action}'",
            error_type="unknown_action", action_requested=action,
            available_actions=["delegate", "plan_and_execute", "get_capabilities"],
        )

    def _delegate(self, task: dict) -> dict:
        agent_id = task.get("agent_id", "")
        subtask = task.get("task", {})
        if not agent_id:
            return {"status": "error", "error": "agent_id nao fornecido"}
        if self._registry:
            try:
                agent = self._registry.load_agent(self.project_id, agent_id)
                result = agent.run(subtask)
                return {
                    "status": "ok",
                    "agent_id": agent_id,
                    "task_result": result.to_dict() if hasattr(result, "to_dict") else str(result),
                }
            except Exception as e:
                return {"status": "error", "agent_id": agent_id, "error": str(e)}
        return {"status": "delegated", "agent_id": agent_id, "task": subtask,
                "note": "Sem registry para execucao real"}

    def _plan_and_execute(self, task: dict) -> dict:
        tasks_list = task.get("tasks", [])
        goal = task.get("goal", "")
        context = task.get("context", "")

        if not tasks_list:
            return {"status": "error", "error": "Nenhuma task fornecida"}

        self._emit_running(f"Executando plano: {goal} ({len(tasks_list)} tasks)")

        # Build dependency map
        completed = set()
        results = {}
        errors = []
        max_iter = 30

        for iteration in range(max_iter):
            executed_this_round = False

            for t in tasks_list:
                name = t["name"]
                if name in completed or name in results:
                    continue

                deps = t.get("depends_on", [])
                if not all(d in completed for d in deps):
                    continue

                agent_id = t["agent_id"]
                subtask = t["task"]
                subtask["task_id"] = f"{name}-{int(time.time())}"

                self._emit_running(f"  -> {agent_id}: {subtask.get('action', '?')} (task: {name})")

                try:
                    if self._registry:
                        agent = self._registry.load_agent(self.project_id, agent_id)
                        result = agent.run(subtask)
                        results[name] = result.to_dict() if hasattr(result, "to_dict") else str(result)
                    else:
                        results[name] = {"status": "simulated", "note": "Sem registry"}
                except Exception as e:
                    err = {"error": str(e), "task": name, "agent": agent_id}
                    errors.append(err)
                    results[name] = err

                completed.add(name)
                executed_this_round = True

            if not executed_this_round:
                break

        # Check for unexecuted tasks
        pending = [t["name"] for t in tasks_list if t["name"] not in completed and t["name"] not in results]

        output = {
            "status": "completed" if not errors else "partial",
            "goal": goal,
            "context": context,
            "total_tasks": len(tasks_list),
            "completed": len(completed),
            "errors": len(errors),
            "results": results,
        }
        if pending:
            output["pending"] = pending
        if errors:
            output["error_details"] = errors

        self._emit_completed(output)
        return output

    def _emit_running(self, msg: str):
        try:
            self._emit(AgentStatus.RUNNING, msg, {})
        except Exception:
            pass

    def _emit_completed(self, output: dict):
        try:
            self._emit(AgentStatus.COMPLETED, "Plano executado", output)
        except Exception:
            pass

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "project_id": self.project_id,
            "subordinates": ["firmware", "visao-llm", "gcode-opt"],
            "actions": ["delegate", "plan_and_execute", "get_capabilities"],
        }
