"""
Agent Factory — CR-10 SE Pipeline Agent
=========================================
Pipeline completo de impressao: STL -> slice -> optimize -> upload -> start -> watchdog.

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


class PipelineAgent(StandardBaseAgent):
    """
    Agente de pipeline de impressao.
    Orquestra o fluxo completo: fatiamento, otimizacao, upload e inicio de impressao.
    """

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "run_pipeline": {
            "description": "Executa pipeline completo: STL -> slice -> optimize -> upload -> start",
            "params": {"stl_path": "str (obrigatorio) - caminho do arquivo STL"},
        },
        "optimize_gcode": {
            "description": "Otimiza arquivo GCode existente (corrige temps, injeta Bed Mesh)",
            "params": {"gcode_path": "str (obrigatorio) - caminho do arquivo GCode"},
        },
        "slice_stl": {
            "description": "Fatia arquivo STL usando PrusaSlicer CLI",
            "params": {"stl_path": "str (obrigatorio)", "config": "str (opcional) - caminho config.ini"},
        },
        "analyze_gcode": {
            "description": "Analisa arquivo GCode em busca de problemas",
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
            agent_id="pipeline",
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

        if action == "run_pipeline":
            return self._run_pipeline(task)
        elif action == "optimize_gcode":
            return self._optimize_gcode(task)
        elif action == "slice_stl":
            return self._slice_stl(task)
        elif action == "analyze_gcode":
            return self._analyze_gcode(task)
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
                cmd, capture_output=True, text=True, timeout=300, cwd=self.working_dir
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-1000:],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Timeout apos 300s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_pipeline(self, task: dict) -> dict:
        stl_path = task.get("stl_path", "")
        if not stl_path:
            return {"status": "error", "error": "stl_path nao fornecido"}
        return self._run_script("pipeline.py", [stl_path])

    def _optimize_gcode(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_script("gcode_optimizer.py", [gcode_path])

    def _slice_stl(self, task: dict) -> dict:
        stl_path = task.get("stl_path", "")
        config = task.get("config", "")
        if not stl_path:
            return {"status": "error", "error": "stl_path nao fornecido"}
        args = [stl_path]
        if config:
            args.extend(["--config", config])
        return self._run_script("pipeline.py", ["--slice-only"] + args)

    def _analyze_gcode(self, task: dict) -> dict:
        gcode_path = task.get("gcode_path", "")
        if not gcode_path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_script("check_errors.py", [gcode_path])

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "working_dir": str(self.working_dir),
            "actions": self.ACTIONS,
        }
