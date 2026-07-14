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
from src.llm import get_provider, LLMProvider

MISSIONS_DIR = Path(".agent-factory") / "missions"
GLOBAL_CONTEXT_FILE = "GLOBAL_CONTEXT.md"


class StandardBaseAgent(AgentBase):
    """
    SDK Padrao para Agentes do Agent Factory.
    Herda de AgentBase para compatibilidade com o loader/registry.

    Cada agente pode ter seu proprio LLM provider para tomada de decisao.
    Defina _DEFAULT_LLM na subclasse ou passe llm_provider via kwargs.
    """

    _DEFAULT_LLM: Optional[str] = None

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

        provider_name = kwargs.get("llm_provider") or self._DEFAULT_LLM
        if provider_name:
            try:
                self._llm: Optional[LLMProvider] = get_provider(provider_name)
            except Exception:
                self._llm = None
        else:
            self._llm = None

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
            # Manter rationale para que agentes downstream (coordinator)
            # possam extrair o texto completo do LLM
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

    # === LLM Thinking Method ===

    def _llm_think(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> Optional[str]:
        """
        Usa o LLM provider do agente para raciocinar sobre um prompt.

        Retorna a resposta do LLM ou None se o provider nao estiver disponivel.
        """
        if not self._llm or not self._llm.is_available():
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self._llm.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.content
        except Exception:
            return None

    # === Gerenciamento de Contexto de 3 Niveis ===

    def get_project_root(self) -> Path:
        """Diretorio raiz do projeto (onde esta GLOBAL_CONTEXT.md)."""
        return self.working_dir if hasattr(self, 'working_dir') and self.working_dir else Path.cwd()

    def load_global_context(self) -> str:
        """Le o GLOBAL_CONTEXT.md do projeto."""
        path = self.get_project_root() / GLOBAL_CONTEXT_FILE
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def get_missions_dir(self) -> Path:
        """Retorna o diretorio base de missoes (.agent-factory/missions/)."""
        return self.get_project_root() / MISSIONS_DIR

    def get_mission_dir(self, mission_id: str) -> Path:
        """Retorna o diretorio de uma missao especifica."""
        return self.get_missions_dir() / mission_id

    def get_mission_input_dir(self, mission_id: str) -> Path:
        return self.get_mission_dir(mission_id) / "input"

    def get_mission_output_dir(self, mission_id: str) -> Path:
        return self.get_mission_dir(mission_id) / "output"

    def get_mission_context_path(self, mission_id: str) -> Path:
        return self.get_mission_input_dir(mission_id) / "Mission_Context.md"

    def load_mission_context(self, mission_id: str) -> str:
        path = self.get_mission_context_path(mission_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def get_task_context_path(self, mission_id: str, task_id: str, agent_id: str) -> Path:
        return self.get_mission_input_dir(mission_id) / "tasks" / task_id / agent_id / "Task_Context.md"

    def load_task_context(self, mission_id: str, task_id: str, agent_id: str) -> str:
        path = self.get_task_context_path(mission_id, task_id, agent_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def get_task_output_dir(self, mission_id: str, task_id: str, agent_id: str) -> Path:
        return self.get_mission_output_dir(mission_id) / "tasks" / task_id / agent_id

    def save_task_result(self, mission_id: str, task_id: str, agent_id: str, content: str):
        """Salva o resultado da execucao de um agente em output/."""
        out_dir = self.get_task_output_dir(mission_id, task_id, agent_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "result.md"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def save_task_artifact(self, mission_id: str, task_id: str, agent_id: str,
                           name: str, content: str, binary: bool = False) -> str:
        """Salva um artefato (codigo, prototipo, relatorio) em output/tasks/.../artifacts/."""
        out_dir = self.get_task_output_dir(mission_id, task_id, agent_id) / "artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / name
        if binary:
            path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        else:
            path.write_text(content, encoding="utf-8")
        return str(path)

    def save_mission_context(self, mission_id: str, content: str) -> str:
        """Escreve o Mission_Context.md no diretorio input/ da missao."""
        path = self.get_mission_context_path(mission_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def save_task_context(self, mission_id: str, task_id: str, agent_id: str, content: str) -> str:
        """Escreve o Task_Context.md para uma tarefa/agente especifico."""
        path = self.get_task_context_path(mission_id, task_id, agent_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def load_all_contexts(self, mission_id: str, task_id: str) -> dict[str, str]:
        """Carrega os 3 niveis de contexto e retorna como dict."""
        return {
            "global": self.load_global_context(),
            "mission": self.load_mission_context(mission_id),
            "task": self.load_task_context(mission_id, task_id, self.agent_id),
        }

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
