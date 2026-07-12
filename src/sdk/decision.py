"""Motor de Decisao — interface + implementacoes para orquestracao."""

import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from src.protocols.schema import TaskOutput, OutputStatus, Decision
from src.llm import LLMProvider


class DecisionContext:
    """Contexto completo para tomada de decisao."""

    def __init__(
        self,
        goal: str,
        plan_name: str,
        step_index: int,
        total_steps: int,
        result: TaskOutput,
        attempt: int = 1,
        max_attempts: int = 3,
        previous_results: Optional[list[TaskOutput]] = None,
    ):
        self.goal = goal
        self.plan_name = plan_name
        self.step_index = step_index
        self.total_steps = total_steps
        self.result = result
        self.attempt = attempt
        self.max_attempts = max_attempts
        self.previous_results = previous_results or []


class DecisionEngine(ABC):
    """
    Interface para motores de decisao.
    Avalia o resultado de um agente e decide o que fazer.
    """

    @abstractmethod
    def decide(self, ctx: DecisionContext) -> tuple[Decision, str]:
        """
        Avalia contexto e retorna (decisao, justificativa).
        """
        ...

    def should_retry(self, ctx: DecisionContext) -> bool:
        decision, _ = self.decide(ctx)
        return decision in (Decision.RETRY, Decision.RETRY_ALTERNATIVE)

    def is_acceptable(self, ctx: DecisionContext) -> bool:
        decision, _ = self.decide(ctx)
        return decision in (Decision.ACCEPT, Decision.SKIP)


class RuleBasedEngine(DecisionEngine):
    """
    Motor baseado em regras fixas.
    Rapido, deterministico, previsivel.
    """

    RULES: dict[OutputStatus, Decision] = {
        OutputStatus.SUCCESS: Decision.ACCEPT,
        OutputStatus.PARTIAL_SUCCESS: Decision.ACCEPT,
        OutputStatus.FAILURE: Decision.RETRY,
        OutputStatus.NEEDS_DIRECTION: Decision.ESCALATE,
        OutputStatus.NEEDS_AUTHORIZATION: Decision.ESCALATE,
        OutputStatus.REJECTED: Decision.ESCALATE,
        OutputStatus.DELEGATED: Decision.ACCEPT,
        OutputStatus.REQUESTED_ACTION: Decision.ESCALATE,
    }

    def __init__(self, max_attempts: int = 3, retry_on: Optional[set[OutputStatus]] = None):
        self.max_attempts = max_attempts
        self.retry_on = retry_on or {OutputStatus.FAILURE, OutputStatus.PARTIAL_SUCCESS}

    def decide(self, ctx: DecisionContext) -> tuple[Decision, str]:
        status = ctx.result.status

        if status in self.retry_on and ctx.attempt < ctx.max_attempts:
            return Decision.RETRY, f"Tentativa {ctx.attempt}/{ctx.max_attempts}, status={status.value}"

        return self.RULES.get(status, Decision.ABORT), f"Regra para status={status.value}"


class LLMDecisionEngine(DecisionEngine):
    """
    Motor baseado em LLM para decisoes que exigem contexto semantico.
    Usa o mesmo provider do coordenador.
    """

    DECISION_PROMPT = """Voce e o motor de orquestracao do Agent Factory Platform.

## Contexto da execucao
Objetivo: {goal}
Passo: {plan_name} ({step_index}/{total_steps})
Tentativa: {attempt}/{max_attempts}

## Resultado do agente
Status: {status}
Sumario: {summary}
Racional: {rationale}
Detalhes: {details}
Acoes disponiveis: {available_actions}

## Decisoes possiveis
- ACCEPT: resultado aceitavel, prosseguir
- RETRY: tentar novamente a mesma acao
- RETRY_ALTERNATIVE: tentar acao diferente
- REPLAN: gerar novo plano do zero
- ESCALATE: escalar para humano/coordenador pai
- SKIP: ignorar este passo e continuar
- ABORT: abortar toda execucao

## Instrucoes
Analise o resultado acima e escolha a decisao mais adequada.
Responda APENAS com JSON: {{"decision": "DECISAO", "justification": "..."}}
"""

    def __init__(self, llm_provider: LLMProvider, max_attempts: int = 3):
        self.llm_provider = llm_provider
        self.max_attempts = max_attempts

    def decide(self, ctx: DecisionContext) -> tuple[Decision, str]:
        details_json = json.dumps(ctx.result.details or {}, ensure_ascii=False)[:2000]
        available = ctx.result.available_actions or []

        prompt = self.DECISION_PROMPT.format(
            goal=ctx.goal[:500],
            plan_name=ctx.plan_name,
            step_index=ctx.step_index,
            total_steps=ctx.total_steps,
            attempt=ctx.attempt,
            max_attempts=ctx.max_attempts,
            status=ctx.result.status.value,
            summary=ctx.result.summary[:300],
            rationale=ctx.result.rationale[:500],
            details=details_json,
            available_actions=json.dumps(available, ensure_ascii=False),
        )

        try:
            resp = self.llm_provider.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=512,
            )
            raw = resp.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            parsed = json.loads(raw)
            decision = Decision(parsed["decision"].lower())
            justification = parsed.get("justification", "")
            return decision, justification
        except Exception as e:
            fallback = RuleBasedEngine(self.max_attempts)
            return fallback.decide(ctx)
