"""
Agent Factory — CR-10 SE Firmware Agent
========================================
Especialista em hardware e firmware da Creality CR-10 SE.
Analisa placa mae, strain gauge, sensores, TMC2209,
firmware Klipper custom (c440x), logs e configs.
Pesquisa forums para solucoes.
"""

import sys
import subprocess
import base64
from pathlib import Path
from typing import Any, Optional

from src.sdk.base import StandardBaseAgent, AgentRole
from src.agents.base import StructuredError
from src.protocols.events import EventNotifier

PRINTER_DIR = Path(r"C:\Users\rafae\Documents\Impressão 3D")
PRINTER_IP = "192.168.18.200"
SSH_USER = "root"
SSH_PASS = "Creality2023"


class FirmwareAgent(StandardBaseAgent):
    """
    Especialista em hardware/firmware CR-10 SE.
    Acoes: SSH, analise de log/config, pesquisa de firmware.
    """

    ACTIONS = {
        "ssh_command": {
            "description": "Executa comando SSH na impressora",
            "params": {"command": "str (obrigatorio)"},
        },
        "read_file": {
            "description": "Le arquivo da impressora (log, config)",
            "params": {"path": "str (obrigatorio) - caminho no servidor"},
        },
        "write_file": {
            "description": "Escreve arquivo na impressora via base64",
            "params": {"path": "str (obrigatorio)", "content": "str (obrigatorio) - conteudo do arquivo"},
        },
        "modify_config": {
            "description": "Modifica parametro no printer.cfg",
            "params": {"param": "str (obrigatorio)", "value": "str (obrigatorio)"},
        },
        "restart_klipper": {
            "description": "Reinicia servico Klipper",
            "params": {},
        },
        "firmware_restart": {
            "description": "Envia FIRMWARE_RESTART para Klipper",
            "params": {},
        },
        "check_klipper_log": {
            "description": "Analisa logs do Klipper em busca de erros",
            "params": {"lines": "int (opcional, default 50)"},
        },
        "analyze_hardware": {
            "description": "Coleta info de hardware via SSH",
            "params": {},
        },
        "research_firmware": {
            "description": "Pesquisa firmware alternativo ou patches",
            "params": {"query": "str (obrigatorio)"},
        },
        "run_script": {
            "description": "Executa script Python local",
            "params": {"script": "str (obrigatorio)", "args": "list (opcional)"},
        },
        "get_capabilities": {
            "description": "Retorna acoes disponiveis",
            "params": {},
        },
    }

    def __init__(self, project_id: str, notifier: EventNotifier, working_dir: Optional[str] = None, **kwargs):
        super().__init__(
            agent_id="firmware", project_id=project_id, notifier=notifier,
            role=AgentRole.WORKER, context_limit_kb=kwargs.get("context_limit_kb", 20.0),
            context_file=kwargs.get("context_file"),
        )
        self.working_dir = Path(working_dir or PRINTER_DIR)

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]
        handler = {
            "ssh_command": self._ssh_command,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "modify_config": self._modify_config,
            "restart_klipper": self._restart_klipper,
            "firmware_restart": self._firmware_restart,
            "check_klipper_log": self._check_klipper_log,
            "analyze_hardware": self._analyze_hardware,
            "research_firmware": self._research_firmware,
            "run_script": self._run_script,
            "get_capabilities": self._get_capabilities,
        }
        if action not in handler:
            raise StructuredError(
                message=f"Acao desconhecida: '{action}'",
                error_type="unknown_action", action_requested=action,
                available_actions=sorted(self.ACTIONS.keys()),
            )
        return handler[action](task)

    def _ssh(self, command: str) -> str:
        result = subprocess.run(
            [sys.executable, str(self.working_dir / "klipper_ssh.py"), "command", command],
            capture_output=True, text=True, timeout=30, cwd=self.working_dir,
        )
        return result.stdout + result.stderr

    def _ssh_command(self, task: dict) -> dict:
        cmd = task.get("command", "")
        if not cmd:
            return {"status": "error", "error": "command nao fornecido"}
        output = self._ssh(cmd)
        return {"status": "ok", "output": output[-3000:]}

    def _read_file(self, task: dict) -> dict:
        path = task.get("path", "")
        if not path:
            return {"status": "error", "error": "path nao fornecido"}
        output = self._ssh(f"cat {path}")
        return {"status": "ok", "content": output[-5000:]}

    def _write_file(self, task: dict) -> dict:
        path = task.get("path", "")
        content = task.get("content", "")
        if not path or not content:
            return {"status": "error", "error": "path e content sao obrigatorios"}
        b64 = base64.b64encode(content.encode()).decode()
        self._ssh(f"echo -n '{b64}' | base64 -d > {path}")
        return {"status": "ok", "path": path}

    def _modify_config(self, task: dict) -> dict:
        param = task.get("param", "")
        value = task.get("value", "")
        if not param or value is None:
            return {"status": "error", "error": "param e value sao obrigatorios"}
        # Use sed to find and replace param in printer.cfg
        self._ssh(f"sed -i 's/^{param}:.*/{param}: {value}/' /usr/data/printer_data/config/printer.cfg")
        return {"status": "ok", "param": param, "value": value}

    def _restart_klipper(self, task: dict) -> dict:
        output = self._ssh("/etc/init.d/klipper restart")
        return {"status": "ok", "output": output[-500:]}

    def _firmware_restart(self, task: dict) -> dict:
        self._ssh("echo 'FIRMWARE_RESTART' > /tmp/printer")
        return {"status": "ok", "message": "FIRMWARE_RESTART enviado"}

    def _check_klipper_log(self, task: dict) -> dict:
        lines = task.get("lines", 50)
        output = self._ssh(f"tail -n {lines} /usr/data/printer_data/logs/klippy.log")
        # Find errors/warnings
        errors = [l for l in output.split("\n") if "ERROR" in l or "WARNING" in l or "shutdown" in l]
        return {"status": "ok", "log_preview": output[-3000:], "errors_found": errors[:20], "total_errors": len(errors)}

    def _analyze_hardware(self, task: dict) -> dict:
        info = {}
        info["cpu"] = self._ssh("cat /proc/cpuinfo | grep -m1 'model name'")
        info["mem"] = self._ssh("free -m | grep Mem")
        info["disk"] = self._ssh("df -h / /rom /usr/data")
        info["klipper_version"] = self._ssh("head -1 /usr/share/klipper/klippy/klippy.py 2>/dev/null || echo 'N/A'")
        info["mcu_temp"] = self._ssh("echo 'GET_POSITION' > /tmp/printer; tail -3 /usr/data/printer_data/logs/klippy.log")
        return {"status": "ok", "hardware": info}

    def _research_firmware(self, task: dict) -> dict:
        return {"status": "ok", "query": task.get("query", ""), "message": "Use webfetch para buscar forums"}

    def _run_script(self, task: dict) -> dict:
        script = task.get("script", "")
        args = task.get("args", [])
        if not script:
            return {"status": "error", "error": "script nao fornecido"}
        script_path = self.working_dir / script
        if not script_path.exists():
            return {"status": "error", "error": f"Script nao encontrado: {script_path}"}
        cmd = [sys.executable, str(script_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=self.working_dir)
        return {"status": "ok" if result.returncode == 0 else "error", "stdout": result.stdout[-3000:], "stderr": result.stderr[-1000:], "returncode": result.returncode}

    def _get_capabilities(self) -> dict:
        return {"agent_id": self.agent_id, "role": self.role.value, "actions": self.ACTIONS}
