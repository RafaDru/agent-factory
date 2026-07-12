"""
Agent Factory — CR-10 SE Coordinator
======================================
Coordenador do projeto cr10se para melhorias na impressora Creality CR-10 SE.
Recebe objetivos em linguagem natural, gera planos via LLM e delega para os workers.

Subordinados:
  - klipper: comunicacao direta com a impressora
  - pipeline: pipeline de impressao (STL -> GCode -> upload -> print)
  - visao: monitoramento por visao computacional
  - resume: retomada de impressoes
  - qa: qualidade e diagnostico
"""

import sys
import json
from pathlib import Path
from typing import Any, Optional

from src.agents.base import AgentBase, AgentRole, StructuredError
from src.protocols.events import EventNotifier
from src.protocols.schema import AgentEvent, AgentStatus
from src.llm import get_provider, LLMProvider

PRINTER_DIR = r"C:\Users\rafae\Documents\Impressao 3D"


class CR10SECoordinator(AgentBase):
    """
    Coordenador do projeto cr10se.
    Planeja e executa melhorias na CR-10 SE delegando para workers especializados.
    """

    ACTIONS = {
        "delegate": {
            "description": "Delega tarefa para um worker e retorna resultado",
            "params": {
                "agent_id": "str (obrigatorio) - klipper | pipeline | visao | resume | qa",
                "task": "dict (obrigatorio) - {action, ...}",
            },
        },
        "plan_and_execute": {
            "description": "Recebe objetivo, gera plano via LLM e executa DAG de tarefas",
            "params": {
                "goal": "str (obrigatorio) - descricao do objetivo",
                "context": "str (opcional) - contexto adicional",
                "tasks": "list[dict] (opcional) - pula LLM e executa diretamente",
            },
        },
        "get_capabilities": {
            "description": "Retorna as acoes disponiveis neste agente",
            "params": {},
        },
    }

    PLAN_SYSTEM_PROMPT = """Voce e o coordenador do projeto cr10se - melhorias na impressora Creality CR-10 SE.
Sua funcao e gerar um plano de execucao em formato JSON a partir de um objetivo.

## Subordinados disponiveis

### klipper
Comunicacao direta com a CR-10 SE via SSH/WebSocket/UDS.
Acoes:
- send_gcode: {"gcode": "M106 S128"}
- read_status: {} 
- get_temps: {}
- modify_config: {"section": "stepper_z", "param": "run_current", "value": "0.800"}
- restart_klipper: {}
- upload_file: {"local_path": "caminho/arquivo.gcode"}
- start_print: {"filename": "arquivo.gcode"}
- check_status: {}
- run_script: {"script": "klipper_ssh.py", "args": ["status"]}

### pipeline
Pipeline de impressao: STL -> slice -> optimize -> upload -> start.
Acoes:
- run_pipeline: {"stl_path": "caminho/arquivo.stl"}
- optimize_gcode: {"gcode_path": "caminho/arquivo.gcode"}
- slice_stl: {"stl_path": "caminho/arquivo.stl", "config": "config.ini"}
- analyze_gcode: {"gcode_path": "caminho/arquivo.gcode"}

### visao
Monitoramento por visao computacional.
Acoes:
- start_monitoring: {"interval": 10}
- analyze_frame: {"image_path": "foto.jpg"}
- check_anomaly: {}
- capture_reference: {"output": "ref.jpg"}
- run_orchestrator: {"interval": 10}

### resume
Retomada de impressoes apos falha.
Acoes:
- analyze_gcode: {"gcode_path": "arquivo.gcode"}
- probe_position: {}
- build_resume: {"gcode_path": "arquivo.gcode", "layer": 16}
- validate_resume: {"gcode_path": "resume.gcode"}
- full_resume: {"gcode_path": "arquivo.gcode"}

### qa
Qualidade e diagnostico.
Acoes:
- validate_gcode: {"gcode_path": "arquivo.gcode"}
- check_config: {}
- run_diagnostics: {}
- check_connection: {}
- check_errors: {}
- quality_pipeline: {"gcode_path": "arquivo.gcode"}

## Contexto da Impressora
- Modelo: Creality CR-10 SE (F003)
- Firmware: Klipper v1.1.0.28
- IP: 192.168.18.200
- SSH: root / Creality2023
- WebSocket: porta 9999
- Camera: MJPG-Streamer porta 8080
- Config: /usr/data/printer_data/config/printer.cfg
- Diretorio de scripts: C:\\Users\\rafae\\Documents\\Impressao 3D

## Parametros Atuais
- max_velocity: 200 mm/s (fabrica: 600)
- max_accel: 2000 mm/s² (fabrica: 8000)
- pressure_advance: 0.030
- Temperature ideal: 210°C bico, 65°C mesa
- Flow: M221 S115 (115%)
- Speed: M220 S50 (50%)

## Regras de Seguranca (OBRIGATORIO)
1. Antes de imprimir: SEMPRE executar G28 + BED_MESH_CALIBRATE
2. NAO usar RESUME da tela (injeta 240°C no hotend)
3. PTFE degrada acima de 215°C - manter bico a 210°C
4. Parafuso de tensao do extruder NAO deve ser apertado demais
5. Confirmar conectividade SSH antes de qualquer comando
6. Toda modificacao no printer.cfg requer restart do Klipper

## Formato de resposta
Responda exclusivamente com um JSON valido:

```json
{
  "plan": [
    {
      "name": "nome-unico",
      "agent_id": "klipper | pipeline | visao | resume | qa",
      "task": {"task_id": "step-id", "action": "...", ...},
      "depends_on": []
    }
  ]
}
```

Regras:
- "name" deve ser unico (usado como identificador de dependencia)
- "depends_on" lista "name"s de tarefas anteriores
- Ordene as tarefas respeitando dependencias
- Paralelize tarefas independentes quando possivel
- Use caminhos relativos ao diretorio C:\\Users\\rafae\\Documents\\Impressao 3D"""

    def __init__(
        self,
        project_id: str,
        notifier: EventNotifier,
        agents: Optional[dict[str, AgentBase]] = None,
        llm_provider: Optional[LLMProvider] = None,
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
        self.llm_provider = llm_provider or get_provider("auto")

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
            message=f"Delegando '{subtask.get('action', '?')}' para {agent_id}",
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

    def _plan_with_llm(self, goal: str, context: str = "") -> list[dict]:
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

        try:
            resp = self.llm_provider.chat(
                messages=[
                    {"role": "system", "content": self.PLAN_SYSTEM_PROMPT},
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
                message=f"Erro ao chamar LLM: {e}",
                error_type="llm_error",
                action_requested="plan_and_execute",
                available_actions=["get_capabilities"],
                doc_path=self.get_doc_path(),
            )

        raw = resp.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise StructuredError(
                message=f"LLM retornou JSON invalido: {e}",
                error_type="invalid_plan_json",
                action_requested="plan_and_execute",
                available_actions=["get_capabilities"],
                doc_path=self.get_doc_path(),
            )

        plan = parsed.get("plan", parsed if isinstance(parsed, list) else [])
        if not plan:
            raise StructuredError(
                message="LLM retornou plano vazio",
                error_type="empty_plan",
                action_requested="plan_and_execute",
                available_actions=["get_capabilities"],
                doc_path=self.get_doc_path(),
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
            message=f"Executando plano: {goal[:120] if goal else 'plano'}",
        ))

        if tasks is None:
            if not goal:
                raise StructuredError(
                    message="Forneca 'goal' ou 'tasks'",
                    error_type="missing_goal",
                    action_requested="plan_and_execute",
                    available_actions=["get_capabilities"],
                    doc_path=self.get_doc_path(),
                )
            try:
                tasks = self._plan_with_llm(goal, context)
            except StructuredError:
                raise
            except Exception as e:
                return {"status": "error", "goal": goal, "error": str(e)}

        self.notifier.emit(AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=AgentStatus.RUNNING,
            task_id="exec-plan",
            project_id=self.project_id,
            message=f"Plano: {len(tasks)} tarefas",
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
                    "reason": f"Dependencias: {missing}",
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
            "status": "ok" if failed == 0 and ok > 0 else ("partial" if failed > 0 else "error"),
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
            "llm_provider": type(self.llm_provider).__name__,
            "actions": self.ACTIONS,
        }
