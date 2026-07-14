"""
Agent Factory — CR-10 SE Quality Assurance Agent
==================================================
Validacao de qualidade para impressao 3D: analise de GCode, configuracao e diagnostico.

Wraps scripts em:
  C:\\Users\\rafae\\Documents\\Impressao 3D
"""

import sys
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.sdk.base import StandardBaseAgent, AgentRole
from src.agents.base import StructuredError
from src.protocols.events import EventNotifier

PRINTER_DIR = Path(r"C:\Users\rafae\Documents\Impressao 3D")


class PrintQAAgent(StandardBaseAgent):
    """
    Agente de qualidade para impressao 3D.
    Valida GCode, configuracoes, executa diagnosticos e verifica estado da impressora.
    """

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "validate_gcode": {
            "description": "Valida arquivo GCode (sintaxe, temperaturas, seguranca)",
            "params": {"gcode_path": "str (obrigatorio) - caminho do arquivo GCode"},
        },
        "check_config": {
            "description": "Verifica configuracoes do printer.cfg na impressora",
            "params": {},
        },
        "run_diagnostics": {
            "description": "Executa diagnostico completo (temperaturas, correntes, sensores)",
            "params": {},
        },
        "check_connection": {
            "description": "Verifica conectividade com a impressora (SSH, WebSocket, HTTP)",
            "params": {},
        },
        "check_errors": {
            "description": "Analisa logs do Klipper em busca de erros recentes",
            "params": {},
        },
        "quality_pipeline": {
            "description": "Executa pipeline de qualidade em um arquivo GCode",
            "params": {"gcode_path": "str (obrigatorio)"},
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
        working_dir: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            agent_id="qa",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
            context_limit_kb=kwargs.get("context_limit_kb", 10.0),
            context_file=kwargs.get("context_file"),
        )
        self.working_dir = Path(working_dir or PRINTER_DIR)

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]

        if action == "validate_gcode":
            return self._validate_gcode(task)
        elif action == "check_config":
            return self._check_config(task)
        elif action == "run_diagnostics":
            return self._run_diagnostics(task)
        elif action == "check_connection":
            return self._check_connection(task)
        elif action == "check_errors":
            return self._check_errors(task)
        elif action == "quality_pipeline":
            return self._quality_pipeline(task)
        elif action == "get_capabilities":
            return self._get_capabilities()
        else:
            available = sorted(self.ACTIONS.keys())
            raise StructuredError(
                message=f"Acão desconhecida: '{action}'",
                error_type="unknown_action",
                action_requested=action,
                available_actions=available,
                doc_path=self.get_doc_path(),
            )

    def _run_script(self, script: str, args: Optional[list[str]] = None) -> dict:
        script_path = self.working_dir / script
        if not script_path.exists():
            return {"status": "error", "error": f"Script nao encontrado: {script_path}"}

        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, cwd=self.working_dir
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-1000:],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Timeout apos 120s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _validate_gcode(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_script("check_errors.py", [gcode_path])

    def _check_config(self, task: dict) -> dict:
        return self._run_script("check_config.py")

    def _run_diagnostics(self, task: dict) -> dict:
        return self._run_script("full_calibration.py")

    def _check_connection(self, task: dict) -> dict:
        return self._run_script("check_klipper_status.py")

    def _check_errors(self, task: dict) -> dict:
        return self._run_script("check_log_real.py")

    def _quality_pipeline(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_script("quality_pipeline.py", [gcode_path])

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "working_dir": str(self.working_dir),
            "actions": self.ACTIONS,
        }
