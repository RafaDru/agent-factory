"""
Agent Factory — Coordenador do Projeto AFP (REAL)
==================================================
Orquestra dev e qa para evoluir a plataforma.
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
from src.sdk.context_tree import ContextTree
from src.llm import get_provider, LLMProvider
from src.eventbus.amqp import AMQPConnection, RPCClient


class AgentFactoryCoordinator(StandardBaseAgent):
    """
    Coordenador do projeto AFP-Team.
    Recebe objetivos de alto nivel, gera planos via LLM e delega
    para os workers do time (dev, qa, designer).
    """

    _DEFAULT_LLM = "auto"

    ACTIONS: dict = {}

    def get_actions(self) -> dict:
        """Retorna ACTIONS com agent_id dinâmico baseado nos subordinados reais."""
        subs = sorted(self._subordinates.keys())
        subs_str = " | ".join(subs) if subs else "dev | qa | designer | negocios | arquiteto"
        return {
            "delegate": {
                "description": f"Delega tarefa para um subordinado ({subs_str}) e retorna resultado",
                "params": {
                    "agent_id": f"str (obrigatorio) - {subs_str}",
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
            "reflect_on_mission": {
                "description": "Apos uma missao, reflete sobre o que aprendeu e persiste na arvore de contexto",
                "params": {
                    "mission_id": "str (obrigatorio) - ID da missao concluida",
                    "goal": "str (obrigatorio) - objetivo original da missao",
                    "steps": "list[dict] (obrigatorio) - steps retornados por plan_and_execute",
                },
            },
            "get_capabilities": {
                "description": "Retorna as acoes disponiveis neste agente",
                "params": {},
            },
        }

    def _build_system_prompt(self) -> str:
        """Gera dinamicamente o PLAN_SYSTEM_PROMPT com base nos subordinados reais."""
        subs = self._subordinates
        subs_list = "\n".join(
            f"- {aid}: {self._describe_agent(subs[aid])}"
            for aid in sorted(subs.keys())
        ) if subs else (
            "- dev: Implementacao de codigo, scripts, edicao\n"
            "- qa: Testes, revisao de codigo, qualidade\n"
            "- designer: Pesquisa UX, prototipos, analise visual\n"
            "- negocios: Backlog, priorizacao, validacao de requisitos\n"
            "- arquiteto: Revisao arquitetural, padroes, coerencia tecnica"
        )

        actions_desc = ""
        for aid in sorted(subs.keys()):
            agent = subs[aid]
            acoes = getattr(agent, "ACTIONS", {})
            # DeclarativeWorker: ler de _config.actions
            if not acoes:
                cfg = getattr(agent, "_config", {})
                acoes = cfg.get("actions", {})
            if acoes:
                actions_desc += f"\n### {aid}\n"
                for act_name in sorted(acoes.keys()):
                    actions_desc += f"- `{act_name}`\n"

        agent_ids = " | ".join(sorted(subs.keys())) if subs else "dev | qa | designer | negocios | arquiteto"

        return f"""Voce e o coordenador do projeto Agent Factory Platform Team (AFP-Team).
Sua funcao e gerar um plano de execucao em formato JSON a partir de um objetivo.

## Subordinados Disponiveis
{subs_list}

## Acoes dos Subordinados{actions_desc}

## Regras de Orquestracao
1. Delegue ao `dev` para implementar incrementalmente (write_file/refactor_code)
2. Delegue ao `qa` para validar (review_code, analyze_project)
3. Delegue ao `designer` para pesquisa UX e prototipos
4. Delegue ao `negocios` para analise de prioridades e requisitos
5. Delegue ao `arquiteto` para revisao arquitetural
6. NUNCA implemente codigo diretamente — delegue ao dev
7. Outputs de tarefas anteriores sao automaticamente passados como contexto para dependentes

## Diretorio de trabalho
C:/Users/rafae/agent-factory

## Formato de Resposta
Responda com JSON contendo "plan" (lista de tarefas):

```json
{{
  "plan": [
    {{
      "name": "exemplo-analise",
      "agent_id": "{next(iter(subs.keys())) if subs else 'dev'}",
      "task": {{
        "task_id": "exemplo-analise",
        "title": "Exemplo de task",
        "action": "read_file",
        "file_path": "src/exemplo.py"
      }},
      "depends_on": []
    }}
  ]
}}
```

Regras:
- "name" unico em kebab-case
- "agent_id": "{agent_ids}"
- "depends_on" lista "name"s de tarefas anteriores
- Ordene por dependencias. Paralelize tarefas independentes.
- Caminhos relativos ao diretorio de trabalho"""

    @staticmethod
    def _describe_agent(agent: Any) -> str:
        """Descreve um agente baseado em suas acoes."""
        acoes = getattr(agent, "ACTIONS", {})
        if not acoes:
            return "Agente sem acoes registradas"
        descs = []
        for name, info in sorted(acoes.items()):
            if name == "get_capabilities":
                continue
            descs.append(info.get("description", name))
        return "; ".join(descs[:3])

    def __init__(
        self,
        project_id: str,
        notifier: EventNotifier,
        agents: Optional[dict[str, StandardBaseAgent]] = None,
        **kwargs,
    ):
        super().__init__(
            agent_id="coordenador",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.COORDINATOR,
            **kwargs,
        )
        self._decision_engine = kwargs.get("decision_engine") or RuleBasedEngine()
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
        elif action == "reflect_on_mission":
            return self._reflect_on_mission(task)
        elif action == "get_capabilities":
            return self._get_capabilities()
        else:
            available = sorted(self.get_actions().keys())
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

        # Tentar usar RabbitMQ se disponivel
        try:
            conn = AMQPConnection("amqp://afp:afp123@localhost:5672/")
            conn.connect()
            rpc = RPCClient(conn, timeout=30.0)
            response = rpc.call(f"task.run.{agent_id}", subtask)
            conn.close()

            # O runtime retorna: {status, agent_id, result: {output, summary, rationale, ...}}
            rb = response.get("result", {}) if response else {}
            rb_status = "success" if response and response.get("status") == "ok" else "failure"
            agent_status = rb.get("status", rb_status)
            if agent_status in ("completed", "success"):
                agent_status = "success"
            return {
                "status": agent_status,
                "agent_id": agent_id,
                "action": subtask.get("action"),
                "result": rb.get("output", rb.get("details", rb)),
                "rationale": rb.get("rationale", rb.get("summary", "")),
                "summary": rb.get("summary", rb.get("rationale", "")),
            }
        except Exception as e:
            logger = __import__("logging").getLogger(__name__)
            logger.debug("Event Bus delegation falhou para %s: %s. Usando in-process.", agent_id, e)
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

        system_prompt = self._build_system_prompt()

        try:
            if not self._llm:
                raise StructuredError("Coordenador sem LLM provider configurado.", error_type="misconfiguration")

            resp = self._llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=16384,
            )
            model_used = resp.model if hasattr(resp, 'model') and resp.model else type(self._llm).__name__
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

    def _generate_mission_id(self, goal: str) -> str:
        """Gera um ID de missao legivel a partir do objetivo."""
        import re
        words = re.findall(r'\w+', goal.lower())
        # Pega palavras significativas (≥3 chars), max 6
        sig = [w for w in words if len(w) >= 3][:6]
        slug = "-".join(sig) if sig else "missao"
        return f"missao-{slug}"

    def _build_mission_context(self, goal: str, context: str, tasks: list[dict], mission_id: str = "") -> str:
        """Monta o Mission_Context.md com objetivo curado, contexto e plano."""
        title = mission_id or self._generate_mission_id(goal)
        lines = [
            f"# Mission Context — {title}",
            "",
            "## Objetivo Curado",
            goal,
        ]
        if context:
            lines += ["", "## Contexto Adicional", context]
        lines += [
            "",
            "## Plano de Trabalho",
            "",
            "| # | Tarefa | Agente | Ação | Depende de |",
            "|---|--------|--------|------|------------|",
        ]
        for i, t in enumerate(tasks, 1):
            name = t.get("name", f"step-{i}")
            agent = t.get("agent_id", "?")
            action = t.get("task", {}).get("action", "?")
            deps = ", ".join(t.get("depends_on", [])) or "—"
            lines.append(f"| {i} | {name} | {agent} | {action} | {deps} |")
        lines += ["", "## Critérios de Aceite"]
        lines += ["- Cada tarefa deve ser validada pelo DecisionEngine"]
        lines += ["- O output de cada tarefa alimenta a proxima dependente"]
        lines += ["- Ao final, todas as tarefas devem estar como 'accept'"]
        return "\n".join(lines)

    def _extract_result_content(self, result: Any) -> str:
        """Extrai conteudo relevante de um resultado, priorizando rationale e campos ricos."""
        if isinstance(result, dict):
            # Priorizar o rationale (texto completo do LLM)
            rationale = result.get("rationale") or result.get("rationale", "")
            if rationale and len(str(rationale)) > 50:
                return str(rationale)
            # Se tiver review/codigo/analise, usar
            for rich_key in ("review", "html_code", "code", "analysis", "suggestions",
                             "plan", "design_systems", "artifact_content", "content"):
                val = result.get(rich_key, "")
                if val and len(str(val)) > 50:
                    return str(val)[:4000]
            # Se for apenas metadados (path, size), tentar ler o arquivo
            file_path = result.get("path") or result.get("file_path", "")
            if file_path and Path(file_path).exists():
                try:
                    content = Path(file_path).read_text(encoding="utf-8")
                    if content:
                        return f"**Arquivo:** {file_path}\n\n```\n{content[:3000]}\n```"
                except Exception:
                    pass
            # Fallback: repr do dict
            return f"```json\n{json.dumps(result, ensure_ascii=False, indent=2)[:2000]}\n```"
        return str(result)[:2000]

    def _build_task_context(self, goal: str, step_name: str, subtask: dict,
                             agent_id: str, dependency_outputs: dict[str, dict]) -> str:
        """Monta o Task_Context.md para um agente especifico."""
        lines = [
            f"# Task Context — {step_name}",
            "",
            "## Objetivo da Missão",
            goal,
            "",
            "## Esta Tarefa",
            f"Agente: {agent_id}",
            f"Ação: {subtask.get('action', '?')}",
            f"Descrição: {subtask.get('title', step_name)}",
        ]
        if dependency_outputs:
            lines += ["", "## Insumos de Tarefas Anteriores"]
            for dep_name, dep_data in dependency_outputs.items():
                result_content = self._extract_result_content(dep_data.get("result", ""))
                if result_content:
                    lines += [
                        f"",
                        f"### Output de: {dep_name} ({dep_data.get('agent_id', '?')})",
                        "",
                        result_content,
                    ]
        task_params = {k: v for k, v in subtask.items() if k not in ("action", "title", "task_id")}
        if task_params:
            lines += ["", "## Parâmetros da Tarefa"]
            lines += [f"- {k}: {v}" for k, v in task_params.items()]
        return "\n".join(lines)

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

        # 1. Gerar plano via LLM se tasks nao foi fornecido
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

        # 2. Gerar mission_id e criar estrutura de diretorios
        mission_id = self._generate_mission_id(goal)
        mission_ctx = self._build_mission_context(goal, context, tasks, mission_id)
        ctx_path = self.save_mission_context(mission_id, mission_ctx)

        # 3. Log do pedido bruto
        raw_path = self.get_mission_input_dir(mission_id) / "raw_request.md"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(
            f"# Raw Request\n\n{json.dumps(task, ensure_ascii=False, indent=2)}",
            encoding="utf-8",
        )

        self.notifier.emit(AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=AgentStatus.RUNNING,
            task_id="exec-plan",
            project_id=self.project_id,
            mission_id=mission_id,
            message=f"Missao '{mission_id}': {len(tasks)} tarefas. Contexto salvo em {ctx_path}",
        ))

        results = []
        completed_ids = set()
        step_outputs: dict[str, dict] = {}

        for idx, step in enumerate(tasks):
            agent_id = step.get("agent_id", "")
            subtask = step.get("task", {})
            depends_on = step.get("depends_on", [])
            step_name = step.get("name", f"step-{idx}")
            task_id = step_name  # Usar nome humanizado para diretorios

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

            # 4. Coletar outputs das dependecias e montar Task_Context.md
            dependency_outputs = {
                dep: step_outputs[dep]
                for dep in depends_on if dep in step_outputs
            }
            task_ctx = self._build_task_context(goal, step_name, subtask, agent_id, dependency_outputs)
            tc_path = self.save_task_context(mission_id, task_id, agent_id, task_ctx)

            # Injetar caminhos dos contextos no subtask para o agente consumir
            enriched_subtask = dict(subtask)
            enriched_subtask["_mission_id"] = mission_id
            enriched_subtask["_task_id"] = task_id
            enriched_subtask["_mission_context_path"] = str(self.get_mission_context_path(mission_id))
            enriched_subtask["_task_context_path"] = str(self.get_task_context_path(mission_id, task_id, agent_id))

            if dependency_outputs:
                enriched_subtask["_dependency_outputs"] = dependency_outputs
                # Tambem injetar como contexto textual para LLM
                dep_text = "## Outputs de tarefas anteriores\n\n"
                for dep_name, dep_data in dependency_outputs.items():
                    dep_text += f"### {dep_name} ({dep_data.get('agent_id', '?')})\n"
                    dep_text += self._extract_result_content(dep_data.get("result", ""))[:3000] + "\n\n"
                enriched_subtask["_dependency_context"] = dep_text

            self.notifier.emit(AgentEvent(
                agent_id=self.agent_id, agent_role=self.role,
                status=AgentStatus.RUNNING,
                task_id=task_id,
                project_id=self.project_id,
                mission_id=mission_id,
                message=f"Passo '{subtask['title']}' -> {agent_id}. Task_Context: {tc_path}",
            ))

            max_attempts = 2
            step_result = None
            step_error = None

            for attempt in range(1, max_attempts + 1):
                try:
                    tr = self._subordinates[agent_id].run(enriched_subtask)
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
                            task_id=task_id,
                            project_id=self.project_id,
                            mission_id=mission_id,
                            message=f"Retry {attempt}/{max_attempts} para '{subtask['title']}'",
                        ))
                    continue

            if step_result is None:
                step_result = TaskOutput.failure(rationale=step_error or "Falha apos todas as tentativas")

            decision, justification, _ = self.handle_subordinate_result(
                result=step_result,
                goal=goal,
                plan_name=step_name,
                step_index=idx,
                total_steps=len(tasks),
                attempt=max_attempts,
                max_attempts=max_attempts,
            )

            # 5. Salvar resultado em output/tasks/<task_id>/<agent_id>/result.md
            body = step_result.rationale or json.dumps(step_result.details or {}, ensure_ascii=False, indent=2)
            result_content = (
                f"# Resultado — {step_name}\n\n"
                f"**Agente:** {agent_id}\n"
                f"**Status:** {step_result.status.value}\n"
                f"**Decisao:** {decision.value}\n"
                f"**Justificativa:** {justification}\n\n"
                f"## Detalhes\n\n{body}"
            )
            self.save_task_result(mission_id, task_id, agent_id, result_content)

            entry = {
                "step": step_name,
                "agent_id": agent_id,
                "status": step_result.status.value,
                "result": step_result.details or step_result.rationale,
                "decision": decision.value,
                "justification": justification,
                "_mission_id": mission_id,
                "_output_path": str(self.get_task_output_dir(mission_id, task_id, agent_id)),
            }
            results.append(entry)

            if decision in (Decision.ACCEPT, Decision.SKIP):
                completed_ids.add(step_name)
                # 6. Armazenar output para uso por tarefas dependentes
                step_outputs[step_name] = {
                    "agent_id": agent_id,
                    "action": subtask.get("action"),
                    "result": step_result.details or step_result.rationale,
                    "status": step_result.status.value,
                    "task_id": task_id,
                }
            elif decision == Decision.ABORT:
                break

        total = len(tasks)
        accepted = sum(1 for r in results if r.get("decision") in ("accept", "skip"))
        failed = sum(1 for r in results if r["status"] in ("failure", "rejected"))

        # Auto-reflexao ao final da missao
        try:
            self._reflect_on_mission({
                "mission_id": mission_id,
                "goal": goal,
                "steps": results,
            })
        except Exception as e:
            self.notifier.emit(AgentEvent(
                agent_id=self.agent_id, agent_role=self.role,
                status=AgentStatus.COMPLETED,
                task_id="reflect",
                project_id=self.project_id,
                mission_id=mission_id,
                message=f"Reflexao falhou (nao critico): {e}",
            ))

        return {
            "status": "ok" if failed == 0 and accepted > 0 else ("partial" if failed > 0 else "error"),
            "mission_id": mission_id,
            "mission_context_path": str(ctx_path),
            "goal": goal,
            "total_steps": total,
            "completed": accepted,
            "failed": failed,
            "skipped": total - accepted - failed,
            "steps": results,
        }

    def _reflect_on_mission(self, task: dict) -> dict:
        mission_id = task.get("mission_id", "")
        goal = task.get("goal", "")
        steps = task.get("steps", [])

        if not mission_id or not steps:
            raise StructuredError(
                message="Forneca 'mission_id' e 'steps' (lista de resultados)",
                error_type="missing_params",
                action_requested="reflect_on_mission",
                available_actions=["get_capabilities"],
                doc_path=self.get_doc_path(),
                hint="Use o output de plan_and_execute como entrada.",
            )

        # Montar sumario dos resultados
        summary_lines = [f"# Retrospectiva da Missao: {mission_id}", "", f"**Objetivo:** {goal}", ""]
        accepted = []
        failed = []
        for s in steps:
            status = s.get("status", "?")
            agent = s.get("agent_id", "?")
            step_name = s.get("step", "?")
            decision = s.get("decision", "?")
            justification = s.get("justification", "")
            summary_lines.append(f"- **{step_name}** ({agent}): {status} / {decision}")
            if justification:
                summary_lines.append(f"  - Justificativa: {justification}")
            if status == "success" and decision == "accept":
                accepted.append(step_name)
            elif status in ("failure", "rejected"):
                failed.append(step_name)

        # Ler resultados detalhados do disco
        details = ""
        for s in steps:
            step_name = s.get("step", "")
            agent_id = s.get("agent_id", "")
            out_dir = self.get_task_output_dir(mission_id, step_name, agent_id)
            result_file = out_dir / "result.md"
            if result_file.exists():
                details += f"\n\n## Resultado: {step_name} ({agent_id})\n\n"
                details += result_file.read_text(encoding="utf-8")[:2000]

        summary = "\n".join(summary_lines)

        # Gerar reflexao via LLM
        reflection = ""
        if self._llm:
            try:
                sys_prompt = (
                    "Voce e o coordenador refletindo sobre uma missao concluida. "
                    "Analise os resultados e extraia aprendizado relevante para FUTURAS missoes. "
                    "Foque em: planejamento (o DAG estava correto?), delegacao (os agentes certos?), "
                    "priorizacao (a missao certa no momento certo?), e licoes gerais. "
                    "Seja conciso (max 3 paragrafos)."
                )
                user_prompt = f"## Missao\n{summary}\n\n## Detalhes\n{details[:3000]}"
                resp = self._llm.chat(
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=2048,
                )
                reflection = resp.content.strip()
            except Exception as e:
                reflection = f"(LLM reflection failed: {e})"

        if not reflection:
            reflection = f"Missao {mission_id}: {len(accepted)} aceitas, {len(failed)} falhas. {summary[:500]}"

        # Persistir na arvore de contexto
        tree = ContextTree(self.project_id, self.agent_id)
        tree.ensure_initialized()

        # Persistir como licoes
        fake_output = TaskOutput.success(summary=reflection[:200])
        tree.persist_learning(
            {"action": "reflect_on_mission", "title": f"missao-{mission_id}"},
            fake_output,
            reflection,
        )

        # Tentar classificar em dominios especificos
        for domain in ("planejamento", "delegacao", "priorizacao"):
            if domain in reflection.lower():
                tree.persist_learning(
                    {"action": "reflect_on_mission", "title": f"missao-{mission_id}-{domain}"},
                    fake_output,
                    reflection,
                )

        # Atualizar CONTEXTO.md com resumo
        ctx_path = self.get_doc_path()
        if Path(ctx_path).exists():
            current = Path(ctx_path).read_text(encoding="utf-8")
            marker = "## Retrospectiva de Missoes"
            entry = (
                f"\n### {mission_id}\n"
                f"- **Objetivo**: {goal[:100]}\n"
                f"- **Resultado**: {len(accepted)}/{len(steps)} tarefas aceitas\n"
            )
            if failed:
                entry += f"- **Falhas**: {', '.join(failed)}\n"
            entry += f"- **Reflexao**: {reflection[:300]}\n"

            if marker in current:
                head, _, tail = current.partition(marker + "\n")
                updated = head + marker + "\n" + entry + "\n" + tail
            else:
                updated = current + "\n\n---\n\n" + marker + "\n" + entry

            Path(ctx_path).write_text(updated, encoding="utf-8")

        return {
            "status": "ok",
            "mission_id": mission_id,
            "accepted": len(accepted),
            "failed": len(failed),
            "total": len(steps),
            "reflection": reflection[:500],
        }

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "subordinates": list(self._subordinates.keys()),
            "llm_provider": type(self._llm).__name__ if self._llm else "None",
            "actions": self.get_actions(),
        }
