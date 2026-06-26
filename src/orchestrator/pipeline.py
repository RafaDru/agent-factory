"""
Agent Factory — Pipeline
=========================
Define e executa sequências pré-determinadas de agentes (playbooks).
Cada passo mapeia um agente + entrada/saída, formando um DAG de execução.

Uso:
    pipeline = Pipeline([
        PipelineStep(id="codegen", agent_id="executor", input={"task": "{input.spec}"}),
        PipelineStep(id="qa", agent_id="tester", input={"code": "{codegen.output}"}),
    ])
    result = pipeline.run(agents, {"spec": "..."})
"""

import json
import re
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..protocols.schema import TaskResult
from ..orchestrator.context_injector import ContextInjector


@dataclass
class PipelineStep:
    id: str
    agent_id: str
    input: dict[str, Any] = field(default_factory=dict)
    output_key: str = "result"
    config: dict[str, Any] = field(default_factory=dict)
    inject: Optional[dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    on_failure: str = "abort"  # abort | skip | continue


@dataclass
class PipelineResult:
    success: bool
    step_results: dict[str, TaskResult]
    final_state: dict[str, Any]
    failed_steps: list[str]
    duration_seconds: float


class Pipeline:
    """
    Sequência de agentes executados em ordem, com suporte a:
    - Injeção de contexto entre passos (ContextInjector)
    - Placeholders: `{step_id.output_key}` no input de passos seguintes
    - Política de falha: abort / skip / continue
    """

    def __init__(
        self,
        steps: list[PipelineStep],
        context_injector: Optional[ContextInjector] = None,
    ):
        self.steps = steps
        self.injector = context_injector or ContextInjector()
        self._step_map = {s.id: s for s in steps}

    def run(
        self,
        agents: dict[str, Any],
        initial_input: Optional[dict] = None,
    ) -> PipelineResult:
        state: dict[str, Any] = {"input": initial_input or {}}
        step_results: dict[str, TaskResult] = {}
        failed_steps: list[str] = []
        start = datetime.utcnow()

        for step in self.steps:
            if step.id in failed_steps:
                continue

            # Context injection before this step
            if step.inject:
                state = self.injector.inject(state, step.inject)

            # Resolve input placeholders
            step_input = self._resolve_input(step, state)

            # Run agent
            agent = agents.get(step.agent_id)
            if not agent:
                failed_steps.append(step.id)
                if step.on_failure == "abort":
                    break
                continue

            try:
                result = agent.run(step_input)
                step_results[step.id] = result
                result_dict = result.model_dump(mode="json") if hasattr(result, 'model_dump') else {"output": result.output}
                state[step.id] = {"output": result_dict}
                if step.output_key and step.output_key != "result":
                    state[step.output_key] = result_dict

                if result.status.value in ("failed", "error"):
                    failed_steps.append(step.id)
                    if step.on_failure == "abort":
                        break
            except Exception as e:
                failed_steps.append(step.id)
                state[step.id] = {"error": str(e)}
                if step.on_failure == "abort":
                    break

        duration = (datetime.utcnow() - start).total_seconds()
        return PipelineResult(
            success=len(failed_steps) == 0,
            step_results=step_results,
            final_state=state,
            failed_steps=failed_steps,
            duration_seconds=duration,
        )

    def _resolve_input(self, step: PipelineStep, state: dict) -> dict:
        """Resolve placeholders no formato {step_id.field}."""
        resolved = {}
        for key, value in step.input.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_placeholders(value, state)
            elif isinstance(value, dict):
                resolved[key] = {
                    k: self._resolve_placeholders(v, state) if isinstance(v, str) else v
                    for k, v in value.items()
                }
            else:
                resolved[key] = value
        return resolved

    def _resolve_placeholders(self, template: str, state: dict) -> Any:
        """Resolve {ref.field.subfield} a partir do estado."""
        def _replace(m: re.Match):
            path = m.group(1).split(".")
            current = state
            for part in path:
                if isinstance(current, dict):
                    current = current.get(part, m.group(0))
                else:
                    return m.group(0)
            if isinstance(current, (dict, list)):
                return json.dumps(current, default=str)
            return str(current) if current is not None else m.group(0)

        return re.sub(r"\{([\w.]+)\}", _replace, template)

    @classmethod
    def from_dict(cls, data: list[dict]) -> "Pipeline":
        steps = [PipelineStep(**step) for step in data]
        return cls(steps)

    def to_dict(self) -> list[dict]:
        return [
            {
                "id": s.id,
                "agent_id": s.agent_id,
                "input": s.input,
                "output_key": s.output_key,
                "config": s.config,
                "inject": s.inject,
                "on_failure": s.on_failure,
            }
            for s in self.steps
        ]
