import os
import time
import inspect
import traceback
from abc import abstractmethod
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from src.protocols.schema import (
    AgentEvent, AgentStatus, AgentRole, TaskResult,
    TaskOutput, OutputStatus, Decision,
)
from src.protocols.events import EventNotifier
from src.agents.base import AgentBase
from src.sdk.decision import DecisionEngine, RuleBasedEngine, DecisionContext
from src.sdk.hooks import HookRegistry, HookPoint, HookContext


class StandardBaseAgent(AgentBase):
    """
    SDK Padrao para Agentes do Agent Factory.
    Herda de AgentBase para compatibilidade com o loader/registry.
    """

    def __init__(self, agent_id: str, project_id: str, notifier: EventNotifier, role: AgentRole, **kwargs):
        super().__init__(
            agent_id=agent_id,
            project_id=project_id,
            notifier=notifier,
            role=role,
            context_file=kwargs.get("context_file"),
            context_limit_kb=kwargs.get("context_limit_kb", 15.0),
        )
        self._start_time = None
        self._subordinates: dict[str, AgentBase] = {}
        self._decision_engine: Optional[DecisionEngine] = None
        self._hooks = HookRegistry()
        self._register_default_hooks()

    def _register_default_hooks(self):
        """Registra hooks padrao: telemetria, decisao, logging."""
        @self._hooks.register(HookPoint.PRE_ACTION)
        def _hook_log_pre(ctx: HookContext):
            ctx.agent.emit(AgentStatus.RUNNING,
                           f"Executando: {ctx.action}", ctx.task)

        @self._hooks.register(HookPoint.POST_ACTION)
        def _hook_log_post(ctx: HookContext):
            if ctx.output and ctx.output.status == OutputStatus.NEEDS_DIRECTION:
                ctx.agent.emit(AgentStatus.WAITING,
                               f"Aguardando direcao: {ctx.action}", ctx.task)

        @self._hooks.register(HookPoint.ON_ERROR)
        def _hook_log_error(ctx: HookContext):
            ctx.agent.emit(AgentStatus.FAILED,
                           f"Erro: {ctx.action} - {ctx.error}", ctx.task)

        @self._hooks.register(HookPoint.ON_DELEGATE)
        def _hook_log_delegate(ctx: HookContext):
            ctx.agent.emit(AgentStatus.RUNNING,
                           f"Delegando '{ctx.action}' para {ctx.delegated_to}", ctx.task)

    def register_subordinate(self, agent_id: str, agent: AgentBase):
        self._subordinates[agent_id] = agent

    def set_decision_engine(self, engine: DecisionEngine):
        self._decision_engine = engine

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def run(self, task: dict[str, Any]) -> TaskResult:
        self._start_time = datetime.utcnow()
        title = task.get("title", task.get("action", "Execucao"))

        # PRE_ACTION hooks
        pre_ctx = HookContext(task=task, agent=self, hook_point=HookPoint.PRE_ACTION,
                              start_time=self._start_time)
        override = self._hooks.run(pre_ctx)
        if pre_ctx._abort or override:
            output_task = override or pre_ctx._override_output or TaskOutput.failure("Abortado por hook")
            payload = output_task.model_dump(mode="json", exclude_none=True)
            return self._build_result(task, AgentStatus.FAILED, payload)

        try:
            raw = self.execute(task)
            output = raw if isinstance(raw, TaskOutput) else TaskOutput.from_execute_output(raw)

            if output.status in (OutputStatus.FAILURE, OutputStatus.REJECTED):
                raise Exception(output.rationale or "Erro nao especificado")

            payload = output.model_dump(mode="json", exclude_none=True)

            # POST_ACTION hooks
            post_ctx = HookContext(task=task, agent=self, hook_point=HookPoint.POST_ACTION,
                                   output=output, start_time=self._start_time)
            self._hooks.run(post_ctx)

            self.emit(AgentStatus.COMPLETED, f"Concluido: {title}", task, payload=payload)
            return self._build_result(task, AgentStatus.COMPLETED, payload)

        except Exception as e:
            error_msg = f"Falha na execucao: {str(e)}"

            # ON_ERROR hooks
            err_ctx = HookContext(task=task, agent=self, hook_point=HookPoint.ON_ERROR,
                                  error=error_msg, start_time=self._start_time)
            self._hooks.run(err_ctx)

            self.emit(AgentStatus.FAILED, error_msg, task, payload={"stack": traceback.format_exc()})
            return self._build_result(task, AgentStatus.FAILED, error=error_msg)

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Agente deve implementar execute()")

    def emit(self, status: AgentStatus, message: str, task: dict, payload: Optional[dict] = None):
        payload = payload or {}
        metrics = {
            "duration_ms": (datetime.utcnow() - self._start_time).total_seconds() * 1000 if self._start_time else 0
        }
        event = AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=status,
            task_id=task.get("task_id", "n/a"),
            project_id=self.project_id,
            message=message,
            payload=payload,
            metrics=metrics,
        )
        self.notifier.emit(event)

    def _build_result(self, task: dict, status: AgentStatus, output: Any = None, error: str = None) -> TaskResult:
        if status == AgentStatus.FAILED and error:
            payload = {"error": error, "status": "error", "action": task.get("action")}
        elif isinstance(output, dict):
            payload = dict(output)
            if "details" in payload and isinstance(payload["details"], dict):
                for k, v in payload.pop("details").items():
                    if k not in payload:
                        payload[k] = v
            payload.pop("rationale", None)
        else:
            payload = {"result": output} if output is not None else {}

        return TaskResult(
            task_id=task.get("task_id", "n/a"),
            agent_id=self.agent_id,
            project_id=self.project_id,
            status=status,
            started_at=self._start_time or datetime.utcnow(),
            completed_at=datetime.utcnow(),
            output=payload,
            summary=f"{status.value.upper()}: {task.get('action', 'Execucao')}",
        )

    # === Delegacao e tratamento de subordinados ===

    def delegate(self, agent_id: str, task: dict) -> TaskOutput:
        if agent_id not in self._subordinates:
            return TaskOutput.failure(
                rationale=f"Subordinado '{agent_id}' nao encontrado. Disponiveis: {list(self._subordinates.keys())}",
                available_actions=["get_capabilities"],
            )

        # ON_DELEGATE hooks
        del_ctx = HookContext(task=task, agent=self, hook_point=HookPoint.ON_DELEGATE,
                              delegated_to=agent_id, start_time=self._start_time)
        self._hooks.run(del_ctx)

        try:
            result = self._subordinates[agent_id].run(task)
            to = TaskOutput(
                status=OutputStatus.SUCCESS,
                summary=result.summary,
                details=result.output,
            )
            if result.status == AgentStatus.FAILED:
                to.status = OutputStatus.FAILURE
                to.rationale = result.summary
            elif result.status == AgentStatus.CANCELLED:
                to.status = OutputStatus.REJECTED
                to.rationale = result.summary
            to.duration_ms = result.total_duration_ms
            return to
        except Exception as e:
            return TaskOutput.failure(rationale=str(e))

    def handle_subordinate_result(
        self,
        result: TaskOutput,
        goal: str = "",
        plan_name: str = "",
        step_index: int = 0,
        total_steps: int = 1,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> tuple[Decision, str, Optional[dict]]:
        """
        Avalia resultado de subordinado e retorna (decisao, justificativa, nova_task).
        Se decision for RETRY/RETRY_ALTERNATIVE, nova_task contem a task corrigida.
        """
        engine = self._decision_engine or RuleBasedEngine(max_attempts)
        ctx = DecisionContext(
            goal=goal,
            plan_name=plan_name,
            step_index=step_index,
            total_steps=total_steps,
            result=result,
            attempt=attempt,
            max_attempts=max_attempts,
        )
        decision, justification = engine.decide(ctx)

        if decision == Decision.RETRY:
            return decision, justification, None
        elif decision == Decision.RETRY_ALTERNATIVE and result.available_actions:
            return decision, justification, {"available_actions": result.available_actions}
        elif decision == Decision.ESCALATE:
            return decision, f"Escalado: {result.rationale}", None
        elif decision == Decision.ABORT:
            return decision, f"Abortado: {result.rationale}", None
        else:
            return decision, justification, None
