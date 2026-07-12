"""Sistema de Hooks — lifecycle callbacks para agentes."""

from enum import Enum
from typing import Any, Callable, Optional, TYPE_CHECKING
from datetime import datetime

from src.protocols.schema import TaskOutput, OutputStatus

if TYPE_CHECKING:
    from src.sdk.base import StandardBaseAgent


class HookPoint(str, Enum):
    """Pontos do ciclo de vida onde hooks podem ser registrados."""
    PRE_ACTION = "pre_action"        # Antes de executar a acao
    POST_ACTION = "post_action"      # Apos execucao bem-sucedida
    ON_ERROR = "on_error"            # Quando ocorre erro
    ON_DELEGATE = "on_delegate"      # Quando delega para subordinado
    ON_DELEGATE_RESULT = "on_delegate_result"  # Quando recebe resultado de delegacao


class HookContext:
    """
    Contexto completo passado para cada hook.
    Cada hook pode ler e modificar o contexto.
    """

    def __init__(
        self,
        task: dict[str, Any],
        agent: "StandardBaseAgent",
        hook_point: HookPoint,
        output: Optional[TaskOutput] = None,
        error: Optional[str] = None,
        start_time: Optional[datetime] = None,
        delegated_to: Optional[str] = None,
        delegated_result: Optional[TaskOutput] = None,
    ):
        self.task = task
        self.agent = agent
        self.hook_point = hook_point
        self.output = output
        self.error = error
        self.start_time = start_time
        self.delegated_to = delegated_to
        self.delegated_result = delegated_result
        self._abort = False
        self._override_output: Optional[TaskOutput] = None

    @property
    def action(self) -> str:
        return self.task.get("action", "?")

    def abort(self, rationale: str = "Execucao abortada por hook"):
        """Interrompe a execucao. Hook PRE_ACTION ou ON_ERROR podem abortar."""
        self._abort = True
        self._override_output = TaskOutput.failure(rationale=rationale)

    def override(self, output: TaskOutput):
        """Substitui o fluxo normal. Hook PRE_ACTION pode interceptar."""
        self._override_output = output
        self._abort = True


# Assinatura: recebe HookContext, retorna None (modifica o contexto in-place)
HookHandler = Callable[[HookContext], None]


class HookRegistry:
    """
    Registro de hooks para um agente.
    Hooks sao executados na ordem em que foram registrados.
    """

    def __init__(self):
        self._hooks: dict[HookPoint, list[HookHandler]] = {
            point: [] for point in HookPoint
        }

    def register(self, point: HookPoint, handler: Optional[HookHandler] = None):
        """
        Registra um handler para um ponto do ciclo.
        Uso: register(HookPoint.PRE_ACTION, minha_funcao)
        Ou como decorator: @registry.register(HookPoint.PRE_ACTION)
        """
        if handler is not None:
            self._hooks[point].append(handler)
            return handler
        # Se chamou como decorator: @registry.register(HookPoint.PRE_ACTION)
        def _decorator(fn: HookHandler) -> HookHandler:
            self._hooks[point].append(fn)
            return fn
        return _decorator

    def unregister(self, point: HookPoint, handler: HookHandler):
        """Remove um handler especifico."""
        if handler in self._hooks[point]:
            self._hooks[point].remove(handler)

    def run(self, ctx: HookContext) -> Optional[TaskOutput]:
        """
        Executa todos os hooks registrados para o ponto do contexto.
        Retorna TaskOutput se algum hook abortou/substituiu a execucao.
        """
        for handler in self._hooks[ctx.hook_point]:
            handler(ctx)
            if ctx._override_output:
                return ctx._override_output
        return None

    def clear(self, point: Optional[HookPoint] = None):
        """Limpa hooks de um ponto especifico ou todos."""
        if point:
            self._hooks[point].clear()
        else:
            for p in HookPoint:
                self._hooks[p].clear()

    def list(self, point: Optional[HookPoint] = None) -> dict[HookPoint, int]:
        """Lista quantidade de hooks registrados."""
        if point:
            return {point: len(self._hooks[point])}
        return {p: len(h) for p, h in self._hooks.items()}
