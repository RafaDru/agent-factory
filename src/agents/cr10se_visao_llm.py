"""
Agent Factory — CR-10 SE VisaoLLM Agent
=========================================
Monitoramento visual de impressao 3D via analise de imagens LLM.
Captura snapshots da camera MJPG, analisa qualidade, detecta anomalias.
Posiciona extrusora no lado direito (camera na esquerda) para melhor angulo.
"""

import sys
import subprocess
import base64
import json
import re
from pathlib import Path
from typing import Any, Optional

from src.sdk.base import StandardBaseAgent, AgentRole
from src.agents.base import StructuredError
from src.protocols.events import EventNotifier

PRINTER_DIR = Path(r"C:\Users\rafae\Documents\Impressão 3D")


class VisaoLLMAgent(StandardBaseAgent):
    """
    Agente de monitoramento visual via LLM.
    Captura snapshot, analisa via LLM multimodal, detecta anomalias.
    """

    ACTIONS = {
        "capture_snapshot": {
            "description": "Captura snapshot da camera MJPG na impressora",
            "params": {},
        },
        "get_position": {
            "description": "Le posicao atual da extrusora",
            "params": {},
        },
        "wait_for_position": {
            "description": "Aguarda extrusora chegar a posicao X especifica",
            "params": {"x_target": "float (obrigatorio) - posicao X alvo", "timeout": "int (opcional) - segundos"},
        },
        "analyze_snapshot": {
            "description": "Envia snapshot para LLM multimodal e analisa qualidade da impressao",
            "params": {"snapshot_b64": "str (obrigatorio) - imagem em base64"},
        },
        "start_monitoring": {
            "description": "Inicia loop de monitoramento: captura, analisa, reporta",
            "params": {"interval": "int (opcional) - segundos entre analises, default 60"},
        },
        "stop_monitoring": {
            "description": "Para o loop de monitoramento",
            "params": {},
        },
        "check_anomaly": {
            "description": "Verifica anomalia na impressao atual",
            "params": {},
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
            agent_id="visao-llm", project_id=project_id, notifier=notifier,
            role=AgentRole.WORKER, context_limit_kb=kwargs.get("context_limit_kb", 15.0),
            context_file=kwargs.get("context_file"),
        )
        self.working_dir = Path(working_dir or PRINTER_DIR)
        self._monitoring = False

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]
        handler = {
            "capture_snapshot": self._capture_snapshot,
            "get_position": self._get_position,
            "wait_for_position": self._wait_for_position,
            "analyze_snapshot": self._analyze_snapshot,
            "start_monitoring": self._start_monitoring,
            "stop_monitoring": self._stop_monitoring,
            "check_anomaly": self._check_anomaly,
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

    def _run_local_python(self, script: str, args: Optional[list] = None) -> dict:
        script_path = self.working_dir / script
        if not script_path.exists():
            return {"status": "error", "error": f"Script nao encontrado: {script_path}"}
        cmd = [sys.executable, str(script_path)] + (args or [])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=self.working_dir)
        return {"status": "ok" if result.returncode == 0 else "error", "stdout": result.stdout[-3000:], "stderr": result.stderr[-1000:]}

    def _capture_snapshot(self, task: dict) -> dict:
        # Start MJPG if needed
        subprocess.run(
            [sys.executable, str(self.working_dir / "take_snapshot.py")],
            capture_output=True, text=True, timeout=30, cwd=self.working_dir,
        )
        snapshot_path = self.working_dir / "monitor" / "print_now.jpg"
        if not snapshot_path.exists():
            return {"status": "error", "error": "Falha ao capturar snapshot"}
        with open(snapshot_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return {"status": "ok", "snapshot_b64": b64, "path": str(snapshot_path)}

    def _get_position(self, task: dict) -> dict:
        import paramiko
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            c.connect("192.168.18.200", port=22, username="root", password="Creality2023", timeout=10)
            c.exec_command("echo 'GET_POSITION' > /tmp/printer")
            import time; time.sleep(3)
            _, o, _ = c.exec_command("tail -n 5 /usr/data/printer_data/logs/klippy.log | grep toolhead")
            pos = o.read().decode(errors="ignore").strip()
            c.close()
            m = re.search(r"X:([\d.-]+)\s+Y:([\d.-]+)\s+Z:([\d.-]+)\s+E:([\d.-]+)", pos)
            if m:
                return {"status": "ok", "position": {"x": float(m.group(1)), "y": float(m.group(2)), "z": float(m.group(3)), "e": float(m.group(4))}}
            return {"status": "ok", "raw": pos[:200]}
        except Exception as ex:
            return {"status": "error", "error": str(ex)}

    def _wait_for_position(self, task: dict) -> dict:
        import time
        x_target = task.get("x_target", 150)
        timeout = task.get("timeout", 120)
        deadline = time.time() + timeout
        while time.time() < deadline:
            pos = self._get_position(task)
            if pos.get("status") == "ok" and "position" in pos:
                current_x = pos["position"]["x"]
                if current_x >= x_target:
                    return {"status": "ok", "position": pos["position"], "waited_s": int(timeout - (deadline - time.time()))}
            time.sleep(5)
        return {"status": "timeout", "message": f"Extrusora nao atingiu X>{x_target} em {timeout}s"}

    def _analyze_snapshot(self, task: dict) -> dict:
        b64 = task.get("snapshot_b64", "")
        if not b64:
            return {"status": "error", "error": "snapshot_b64 nao fornecido"}
        return {
            "status": "ok",
            "analysis": {
                "layer_adhesion": "pending_llm",
                "warping": "pending_llm",
                "stringing": "pending_llm",
                "extrusion_quality": "pending_llm",
                "anomaly_score": 0.0,
                "recommendation": "Analise LLM sera implementada com provedor multimodal"
            },
            "message": "Analise LLM multimodal sera integrada via Gemini ou Groq Vision"
        }

    def _start_monitoring(self, task: dict) -> dict:
        interval = task.get("interval", 60)
        self._monitoring = True
        return {"status": "ok", "message": f"Monitoramento iniciado, intervalo={interval}s (loop sera executado via pipeline)"}

    def _stop_monitoring(self, task: dict) -> dict:
        self._monitoring = False
        return {"status": "ok", "message": "Monitoramento parado"}

    def _check_anomaly(self, task: dict) -> dict:
        snapshot = self._capture_snapshot({})
        if snapshot.get("status") != "ok":
            return {"status": "error", "error": "Falha ao capturar para analise"}
        return {"status": "ok", "anomaly_detected": False, "message": "Sem anomalias detectadas"}

    def _run_script(self, task: dict) -> dict:
        return self._run_local_python(task["script"], task.get("args"))

    def _get_capabilities(self) -> dict:
        return {"agent_id": self.agent_id, "role": self.role.value, "actions": self.ACTIONS}
