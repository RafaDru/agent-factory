"""
Agent Factory — CR-10 SE Klipper Agent
========================================
Comunicacao direta com a Creality CR-10 SE via SSH, WebSocket e Klipper UDS.

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
PRINTER_IP = "192.168.18.200"
SSH_USER = "root"
SSH_PASS = "Creality2023"


class KlipperAgent(StandardBaseAgent):
    """
    Agente de comunicacao com a CR-10 SE.
    Envia GCode via SSH/UDS, le status, modifica config, faz upload.
    """

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "send_gcode": {
            "description": "Envia comando GCode para a impressora via SSH echo > /tmp/printer",
            "params": {"gcode": "str (obrigatorio) - comando GCode (ex: M106 S128)"},
        },
        "read_status": {
            "description": "Le status atual da impressora via WebSocket",
            "params": {},
        },
        "get_temps": {
            "description": "Le temperaturas atuais (bico, mesa, ambiente)",
            "params": {},
        },
        "modify_config": {
            "description": "Modifica parametro no printer.cfg via SSH",
            "params": {"section": "str (obrigatorio) - ex: stepper_z", "param": "str (obrigatorio) - ex: run_current", "value": "str (obrigatorio) - ex: 0.800"},
        },
        "restart_klipper": {
            "description": "Reinicia o servico Klipper via SSH",
            "params": {},
        },
        "upload_file": {
            "description": "Faz upload de arquivo GCode para a impressora via HTTP",
            "params": {"local_path": "str (obrigatorio) - caminho do arquivo local"},
        },
        "start_print": {
            "description": "Inicia impressao de um arquivo na impressora",
            "params": {"filename": "str (obrigatorio) - nome do arquivo em /usr/data/printer_data/gcodes/"},
        },
        "check_status": {
            "description": "Verifica conectividade e estado geral da impressora",
            "params": {},
        },
        "run_script": {
            "description": "Executa script Python do diretorio Impressao 3D na impressora",
            "params": {"script": "str (obrigatorio) - nome do script (ex: klipper_ssh.py)", "args": "list[str] (opcional)"},
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
            agent_id="klipper",
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

        if action == "send_gcode":
            return self._send_gcode(task)
        elif action == "read_status":
            return self._read_status(task)
        elif action == "get_temps":
            return self._get_temps(task)
        elif action == "modify_config":
            return self._modify_config(task)
        elif action == "restart_klipper":
            return self._restart_klipper(task)
        elif action == "upload_file":
            return self._upload_file(task)
        elif action == "start_print":
            return self._start_print(task)
        elif action == "check_status":
            return self._check_status(task)
        elif action == "run_script":
            return self._run_script(task)
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

    def _run_python(self, script: str, args: Optional[list[str]] = None) -> dict:
        """Executa script Python no diretorio Impressao 3D via subprocess."""
        script_path = self.working_dir / script
        if not script_path.exists():
            return {"status": "error", "error": f"Script nao encontrado: {script_path}"}

        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=self.working_dir
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-1000:],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": f"Timeout apos 60s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _send_gcode(self, task: dict) -> dict:
        gcode = task.get("gcode", "")
        if not gcode:
            return {"status": "error", "error": "GCode nao fornecido"}
        return self._run_python("klipper_ssh.py", ["command", gcode])

    def _read_status(self, task: dict) -> dict:
        return self._run_python("klipper_ssh.py", ["status"])

    def _get_temps(self, task: dict) -> dict:
        return self._run_python("check_status.py")

    def _modify_config(self, task: dict) -> dict:
        section = task.get("section", "")
        param = task.get("param", "")
        value = task.get("value", "")
        if not section or not param or not value:
            return {"status": "error", "error": "section, param e value sao obrigatorios"}
        sed_cmd = rf"sed -i '/^\[{section}\]/,/^\[/ s/^{param}:.*/{param}: {value}/' /usr/data/printer_data/config/printer.cfg"
        return self._run_python("klipper_ssh.py", ["command", sed_cmd])

    def _restart_klipper(self, task: dict) -> dict:
        return self._run_python("klipper_ssh.py", ["command", "systemctl restart klipper"])

    def _upload_file(self, task: dict) -> dict:
        local_path = task.get("local_path", "")
        if not local_path:
            return {"status": "error", "error": "local_path nao fornecido"}
        return self._run_python("upload_http.py", [local_path])

    def _start_print(self, task: dict) -> dict:
        filename = task.get("filename", "")
        if not filename:
            return {"status": "error", "error": "filename nao fornecido"}
        return self._run_python("creality_ws.py", ["print", filename])

    def _check_status(self, task: dict) -> dict:
        return self._run_python("check_klipper_status.py")

    def _run_script(self, task: dict) -> dict:
        script = task.get("script", "")
        args = task.get("args", [])
        if not script:
            return {"status": "error", "error": "script nao fornecido"}
        return self._run_python(script, args)

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "working_dir": str(self.working_dir),
            "printer": {"ip": PRINTER_IP, "hostname": "CR10SE-3C89", "model": "CR-10 SE"},
            "actions": self.ACTIONS,
        }
