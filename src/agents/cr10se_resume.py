"""
Agent Factory — CR-10 SE Resume Agent
=======================================
Gerenciamento de retomada de impressoes 3D apos falha.

Wraps scripts em:
  C:\\Users\\rafae\\Documents\\Impressao 3D
"""

import sys
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.agents.base import AgentBase, AgentRole, StructuredError
from src.protocols.events import EventNotifier

PRINTER_DIR = Path(r"C:\Users\rafae\Documents\Impressao 3D")


class ResumeAgent(AgentBase):
    """
    Agente de retomada de impressao.
    Analisa GCode, probe de posicao, constroi GCode de retomada e valida.
    """

    ACTIONS = {
        "analyze_gcode": {
            "description": "Analisa arquivo GCode e identifica ultima layer completa",
            "params": {"gcode_path": "str (obrigatorio) - caminho do arquivo GCode"},
        },
        "probe_position": {
            "description": "Faz probe da posicao atual do nozzle e mede descolamento",
            "params": {},
        },
        "build_resume": {
            "description": "Constroi GCode de retomada a partir da ultima layer valida",
            "params": {"gcode_path": "str (obrigatorio)", "layer": "int (opcional) - layer alvo"},
        },
        "validate_resume": {
            "description": "Valida GCode de retomada (sintaxe, seguranca, compatibilidade)",
            "params": {"gcode_path": "str (obrigatorio) - caminho do GCode de retomada"},
        },
        "full_resume": {
            "description": "Executa retomada completa: analyze -> probe -> build -> validate -> upload -> start",
            "params": {"gcode_path": "str (obrigatorio) - caminho do GCode original"},
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
            agent_id="resume",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
            context_limit_kb=kwargs.get("context_limit_kb", 15.0),
            context_file=kwargs.get("context_file"),
        )
        self.working_dir = Path(working_dir or PRINTER_DIR)

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]

        if action == "analyze_gcode":
            return self._analyze_gcode(task)
        elif action == "probe_position":
            return self._probe_position(task)
        elif action == "build_resume":
            return self._build_resume(task)
        elif action == "validate_resume":
            return self._validate_resume(task)
        elif action == "full_resume":
            return self._full_resume(task)
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

    def _analyze_gcode(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_script("resume_toolkit.py", ["analyze", gcode_path])

    def _probe_position(self, task: dict) -> dict:
        return self._run_script("resume_toolkit.py", ["probe"])

    def _build_resume(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        layer = task.get("layer")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        args = ["build", gcode_path]
        if layer is not None:
            args.extend(["--layer", str(layer)])
        return self._run_script("resume_toolkit.py", args)

    def _validate_resume(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_script("resume_toolkit.py", ["validate", gcode_path])

    def _full_resume(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_script("resume_toolkit.py", ["full", gcode_path])

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "working_dir": str(self.working_dir),
            "actions": self.ACTIONS,
        }
