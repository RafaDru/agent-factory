"""
Agent Factory — CR-10 SE Vision Agent
=======================================
Monitoramento por visao computacional durante impressao 3D.

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


class VisionAgent(StandardBaseAgent):
    """
    Agente de visao computacional para monitoramento de impressao.
    Detecta anomalias, patinacao da extrusora, e crescimento da peca.
    """

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "start_monitoring": {
            "description": "Inicia monitoramento visual em background (print_health_monitor.py)",
            "params": {"interval": "int (opcional) - intervalo entre frames (padrao 10)"},
        },
        "analyze_frame": {
            "description": "Analisa um frame capturado da camera",
            "params": {"image_path": "str (opcional) - caminho da imagem (padrao: captura ao vivo)"},
        },
        "check_anomaly": {
            "description": "Verifica se ha anomalia na impressao atual via visao computacional",
            "params": {},
        },
        "capture_reference": {
            "description": "Captura foto de referencia para comparacao futura",
            "params": {"output": "str (opcional) - caminho de saida (padrao: reference.jpg)"},
        },
        "run_orchestrator": {
            "description": "Inicia o VisionOrchestrator com monitoramento ciclico",
            "params": {"interval": "int (opcional) - intervalo em segundos (padrao 10)"},
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
            agent_id="visao",
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

        if action == "start_monitoring":
            return self._start_monitoring(task)
        elif action == "analyze_frame":
            return self._analyze_frame(task)
        elif action == "check_anomaly":
            return self._check_anomaly(task)
        elif action == "capture_reference":
            return self._capture_reference(task)
        elif action == "run_orchestrator":
            return self._run_orchestrator(task)
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

    def _start_monitoring(self, task: dict) -> dict:
        interval = task.get("interval", 10)
        return self._run_script("print_health_monitor.py", ["--interval", str(interval)])

    def _analyze_frame(self, task: dict) -> dict:
        image_path = task.get("image_path", "")
        if image_path:
            return self._run_script("print_vision.py", ["--analyze", image_path])
        return self._run_script("print_vision.py", ["--analyze-live"])

    def _check_anomaly(self, task: dict) -> dict:
        return self._run_script("print_vision.py", ["--check-anomaly"])

    def _capture_reference(self, task: dict) -> dict:
        output = task.get("output", "reference.jpg")
        return self._run_script("snapshot_monitor.py", ["--output", output])

    def _run_orchestrator(self, task: dict) -> dict:
        interval = task.get("interval", 10)
        return self._run_script("print_vision.py", ["--orchestrator", "--interval", str(interval)])

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "working_dir": str(self.working_dir),
            "actions": self.ACTIONS,
        }
