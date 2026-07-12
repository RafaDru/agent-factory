"""
Agent Factory — Coordenador do Projeto agent-factory-dev (REAL)
===============================================================
Orquestra agentes-factory-dev e qa para evoluir a plataforma.
Usa LLM (Groq/Ollama) para gerar planos autonomamente a partir de objetivos.
"""

import sys
import json
from pathlib import Path
from typing import Any, Optional

from src.agents.base import StructuredError
from src.protocols.events import EventNotifier
from src.protocols.schema import AgentEvent, AgentStatus, AgentRole, TaskOutput, OutputStatus, Decision
from src.sdk.base import StandardBaseAgent
from src.sdk.decision import DecisionEngine, RuleBasedEngine
from src.llm import get_provider, LLMProvider


class AgentFactoryCoordinator(StandardBaseAgent):
    """
    Coordenador do projeto agent-factory-dev.
    Recebe objetivos de alto nivel, gera planos via LLM e delega
    para agent-factory-dev e qa.
    """

    ACTIONS = {
        "delegate": {
            "description": "Delega tarefa para agente-factory-dev ou qa e retorna resultado",
            "params": {
                "agent_id": "str (obrigatorio) - desenvolvedor | qa | designer",
                "task": "dict (obrigatorio) - {action, ...}",
            },
        },
        "plan_and_execute": {
            "description": "Recebe objetivo, gera plano via LLM e executa DAG de tarefas",
            "params": {
                "goal": "str (obrigatorio) - descricao do objetivo em linguagem natural",
                "context": "str (opcional) - contexto adicional ou restricoes",
                "tasks": "list[dict] (opcional) - se fornecido, pula o LLM e executa diretamente",
            },
        },
        "get_capabilities": {
            "description": "Retorna as acoes disponiveis neste agente",
            "params": {},
        },
    }

    PLAN_SYSTEM_PROMPT = """Voce e o coordenador do projeto Agent Factory (agent-factory-dev).
Sua funcao e gerar um plano de execucao em formato JSON a partir de um objetivo.

## Regra de Ouro da Orquestração
Você é o Coordenador. Sua responsabilidade é garantir a qualidade.
1. Receba objetivo.
2. Delegue sempre ao `designer` para propor o design/protótipo antes de qualquer código.
3. Delegue ao `desenvolvedor` a implementação baseada nos artefatos do designer.
4. Delegue ao `qa` a validação final.
5. Somente marque como COMPLETED após o QA validar. Se qualquer etapa falhar, aborte e reporte.

## Subordinados disponiveis (use estes nomes exatos)
- designer: Planejamento gráfico, protótipos HTML/CSS, UX.
- desenvolvedor: Implementação de código, scripts, edição de arquivos.
- qa: Testes, validação e qualidade.

## Formato de resposta
Responda exclusivamente com um JSON contendo uma chave "plan" (lista de tarefas com depends_on obrigatório).

## Diretorio de trabalho
C:/Users/rafae/agent-factory

## Regras de Execucao (OBRIGATORIO)
- Toda tarefa delegada ao agente 'desenvolvedor' DEVE ser seguida por uma tarefa de verificacao do agente 'qa'.
- A tarefa de QA deve ter 'depends_on' apontando para o nome da tarefa do desenvolvedor.
- O coordenador deve garantir essa cadeia de validacao antes de marcar a implementacao como concluida.
- Os agentes disponiveis sao: desenvolvedor (codigo), qa (testes/validacao), designer (design/prototipo).

## Acoes disponiveis por agente

### desenvolvedor (codigo, arquivos, scripts)
- `read_file` params: file_path
- `write_file` params: file_path, content
- `edit_file` params: file_path, old_string, new_string
- `list_directory` params: path, pattern
- `run_script` params: script_path, args (opcional)
- `run_tests` params: path, args (opcional)
- `run_git` params: args
- `rename_file` params: src, dst
- `delete_file` params: file_path

### qa (testes, validacao, qualidade)
- `run_tests` params: path, args (opcional)
- `validate_python_syntax` params: file_path
- `analyze_artifact` params: file_path, checks (opcional)
- `lint` params: path
- `file_exists` params: file_path

### designer (design, prototipos)
- `design_ui` params: prompt
- `prototype` params: prompt
- `analyze_ux` params: prompt

## Formato de resposta
Responda exclusivamente com um JSON valido contendo uma chave "plan" com uma lista de tarefas:

```json
{
  "plan": [
    {
      "name": "criar-arquivo-teste",
      "agent_id": "desenvolvedor",
      "task": {
        "task_id": "step-001",
        "title": "Criar arquivo de teste",
        "action": "write_file",
        "file_path": "TESTE.txt",
        "content": "conteudo do arquivo"
      },
      "depends_on": []
    },
    {
      "name": "verificar-arquivo",
      "agent_id": "qa",
      "task": {
        "task_id": "step-002",
        "title": "Validar arquivo",
        "action": "file_exists",
        "file_path": "TESTE.txt"
      },
      "depends_on": ["criar-arquivo-teste"]
    }
  ]
}
```

Regras:
- "name" deve ser unico (usado como identificador de dependencia)
- "agent_id" deve ser "desenvolvedor" (codigo), "qa" (testes), ou "designer" (design)
- "depends_on" lista "name"s de tarefas que devem ser concluidas antes
- Nao inclua tarefas dependentes de si mesmas
- Ordene as tarefas respeitando as dependencias
- Se possivel, paralelize tarefas independentes
- Use caminhos relativos ao diretorio de trabalho"""

    def __init__(
        self,
        project_id: str,
        notifier: EventNotifier,
        agents: Optional[dict[str, StandardBaseAgent]] = None,
        llm_provider: Optional[LLMProvider] = None,
        decision_engine: Optional[DecisionEngine] = None,
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
        self.llm_provider = llm_provider or get_provider("auto")
        self._decision_engine = decision_engine or RuleBasedEngine()
        if agents:
            for aid, agent in agents.items():
                self.register_subordinate(aid, agent)

    def set_subordinates(self, agents: dict[str, StandardBaseAgent]):
        for aid, agent in agents.items():
            self.register_subordinate(aid, agent)

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
                hint=f"Use action=get_capabilities para ver as acoes disponiveis.",
            )

    def _delegate(self, task: dict) -> dict:
        agent_id = task.get("agent_id", "")
        subtask = task.get("task", {})
        output = self.delegate(agent_id, subtask)
        return {
            "status": output.status.value,
            "agent_id": agent_id,
            "action": subtask.get("action"),
            "result": output.details,
            "rationale": output.rationale,
            "summary": output.summary,
        }

    def _plan_with_llm(self, goal: str, context: str = "") -> list[dict]:
        """Gera plano de tarefas chamando o LLM."""
        user_prompt = f"## Objetivo\n{goal}\n"
        if context:
            user_prompt += f"\n## Contexto\n{context}\n"
        user_prompt += "\nGere o plano JSON para atingir este objetivo."

        self.notifier.emit(AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=AgentStatus.RUNNING,
            task_id="llm-plan",
            project_id=self.project_id,
            message=f"Gerando plano via LLM para: {goal[:100]}",
        ))

        system_prompt = self.PLAN_SYSTEM_PROMPT

        try:
            resp = self.llm_provider.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            model_used = resp.model if hasattr(resp, 'model') and resp.model else type(self.llm_provider).__name__
            self.notifier.emit(AgentEvent(
                agent_id=self.agent_id, agent_role=self.role,
                status=AgentStatus.RUNNING, task_id="llm-model",
                project_id=self.project_id,
                message=f"Modelo: {model_used}",
                metrics={"model": model_used},
            ))
        except Exception as e:
            raise StructuredError(
                message=f"Erro ao chamar LLM para gerar plano: {e}",
                error_type="llm_error",
                action_requested="plan_and_execute",
                available_actions=["get_capabilities"],
                doc_path=self.get_doc_path(),
                hint="Verifique se o provedor LLM (Groq/Ollama) esta disponivel.",
            )

        raw = resp.content.strip()
        # Extrair JSON do bloco ```json ... ``` se presente
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise StructuredError(
                message=f"LLM retornou JSON invalido: {e}\nResposta bruta: {raw[:500]}",
                error_type="invalid_plan_json",
                action_requested="plan_and_execute",
                available_actions=["get_capabilities"],
                doc_path=self.get_doc_path(),
                hint="O LLM nao gerou um JSON valido. Tente novamente ou forneca as tasks manualmente.",
            )

        plan = parsed.get("plan", parsed if isinstance(parsed, list) else [])
        if not plan:
            raise StructuredError(
                message="LLM retornou plano vazio",
                error_type="empty_plan",
                action_requested="plan_and_execute",
                available_actions=["get_capabilities"],
                doc_path=self.get_doc_path(),
                hint="O LLM nao gerou nenhuma tarefa no plano.",
            )

        return plan

    def _plan_and_execute(self, task: dict) -> dict:
        goal = task.get("goal", "")
        context = task.get("context", "")
        tasks = task.get("tasks", None)

        self.notifier.emit(AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=AgentStatus.RUNNING,
            task_id="plan",
            project_id=self.project_id,
            message=f"Executando plano: {goal[:120]}" if goal else "Executando plano",
        ))

        # Gerar plano via LLM se tasks nao foi fornecido
        if tasks is None:
            if not goal:
                raise StructuredError(
                    message="Forneca 'goal' (objetivo) ou 'tasks' (lista manual)",
                    error_type="missing_goal",
                    action_requested="plan_and_execute",
                    available_actions=["get_capabilities"],
                    doc_path=self.get_doc_path(),
                    hint="Use 'goal' para gerar plano via LLM ou 'tasks' para fornecer manualmente.",
                )
            try:
                tasks = self._plan_with_llm(goal, context)
            except StructuredError:
                raise
            except Exception as e:
                return {
                    "status": "error",
                    "goal": goal,
                    "error": f"Falha ao gerar plano: {e}",
                }

        self.notifier.emit(AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=AgentStatus.RUNNING,
            task_id="exec-plan",
            project_id=self.project_id,
            message=f"Plano gerado: {len(tasks)} tarefas para {goal[:80]}" if goal else f"Plano gerado: {len(tasks)} tarefas",
        ))

        results = []
        completed_ids = set()

        for idx, step in enumerate(tasks):
            agent_id = step.get("agent_id", "")
            subtask = step.get("task", {})
            depends_on = step.get("depends_on", [])
            step_name = step.get("name", f"step-{idx}")

            missing = [d for d in depends_on if d not in completed_ids]
            if missing:
                results.append({
                    "step": step_name,
                    "agent_id": agent_id,
                    "status": "skipped",
                    "reason": f"Dependencias nao concluidas: {missing}",
                })
                continue

            if "title" not in subtask:
                subtask["title"] = step_name

            self.notifier.emit(AgentEvent(
                agent_id=self.agent_id, agent_role=self.role,
                status=AgentStatus.RUNNING,
                task_id=subtask.get("task_id", step_name),
                project_id=self.project_id,
                message=f"Passo '{subtask['title']}' -> {agent_id}",
            ))

            max_attempts = 2
            step_result = None
            step_error = None

            for attempt in range(1, max_attempts + 1):
                try:
                    tr = self._subordinates[agent_id].run(subtask)
                    to = TaskOutput(
                        status=OutputStatus.SUCCESS,
                        summary=tr.summary,
                        details=tr.output,
                    )
                    if tr.status == AgentStatus.FAILED:
                        to.status = OutputStatus.FAILURE
                        to.rationale = tr.summary
                    step_result = to
                    break
                except Exception as e:
                    step_error = str(e)
                    if attempt < max_attempts:
                        self.notifier.emit(AgentEvent(
                            agent_id=self.agent_id, agent_role=self.role,
                            status=AgentStatus.RUNNING,
                            task_id=subtask.get("task_id", step_name),
                            project_id=self.project_id,
                            message=f"Retry {attempt}/{max_attempts} para '{subtask['title']}'",
                        ))
                    continue

            if step_result is None:
                step_result = TaskOutput.failure(rationale=step_error or "Falha apos todas as tentativas")

            # Usar motor de decisao para avaliar o resultado
            decision, justification, _ = self.handle_subordinate_result(
                result=step_result,
                goal=goal,
                plan_name=step_name,
                step_index=idx,
                total_steps=len(tasks),
                attempt=max_attempts,
                max_attempts=max_attempts,
            )

            entry = {
                "step": step_name,
                "agent_id": agent_id,
                "status": step_result.status.value,
                "result": step_result.details or step_result.rationale,
                "decision": decision.value,
                "justification": justification,
            }
            results.append(entry)

            if decision in (Decision.ACCEPT, Decision.SKIP):
                completed_ids.add(step_name)
            elif decision == Decision.ABORT:
                break

        total = len(tasks)
        accepted = sum(1 for r in results if r.get("decision") in ("accept", "skip"))
        failed = sum(1 for r in results if r["status"] in ("failure", "rejected"))

        return {
            "status": "ok" if failed == 0 and accepted > 0 else ("partial" if failed > 0 else "error"),
            "goal": goal,
            "total_steps": total,
            "completed": accepted,
            "failed": failed,
            "skipped": total - accepted - failed,
            "steps": results,
        }

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "subordinates": list(self._subordinates.keys()),
            "llm_provider": type(self.llm_provider).__name__,
            "actions": self.ACTIONS,
        }
