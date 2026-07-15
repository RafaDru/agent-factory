"""
Agent Factory — CR-10 SE GCode Optimizer Agent
===============================================
Especialista em otimizacao extrema de GCode para CR-10 SE.
Otimiza caminhos, temperaturas, bed mesh, PA, anti-warping.
Gera GCode customizado para calibracao.
"""

import sys
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.sdk.base import StandardBaseAgent, AgentRole
from src.agents.base import StructuredError
from src.protocols.events import EventNotifier

PRINTER_DIR = Path(r"C:\Users\rafae\Documents\Impressão 3D")


class GCodeOptimizerAgent(StandardBaseAgent):
    """
    Otimizacao extrema de GCode para CR-10 SE.
    """

    ACTIONS = {
        "optimize": {
            "description": "Otimiza GCode existente (caminhos, temp, mesh, PA)",
            "params": {"gcode_path": "str (obrigatorio) - caminho do arquivo .gcode"},
        },
        "generate_calibration": {
            "description": "Gera GCode de calibracao (cube, retraction tower)",
            "params": {"type": "str (obrigatorio) - cube, retraction, temp_tower"},
        },
        "analyze_gcode": {
            "description": "Analisa GCode: tempo, camadas, problemas",
            "params": {"gcode_path": "str (obrigatorio)"},
        },
        "fix_temperatures": {
            "description": "Corrige sequencia de temperaturas para CR-10 SE",
            "params": {"gcode_path": "str (obrigatorio)"},
        },
        "inject_bed_mesh": {
            "description": "Adiciona BED_MESH_CALIBRATE no GCode",
            "params": {"gcode_path": "str (obrigatorio)"},
        },
        "set_pressure_advance": {
            "description": "Ajusta SET_PRESSURE_ADVANCE no GCode",
            "params": {"gcode_path": "str (obrigatorio)", "pa_value": "float (opcional, default 0.03)"},
        },
        "optimize_paths": {
            "description": "Otimiza caminhos da extrusora (reduz travels)",
            "params": {"gcode_path": "str (obrigatorio)"},
        },
        "estimate_time": {
            "description": "Estima tempo de impressao baseado no GCode",
            "params": {"gcode_path": "str (obrigatorio)"},
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
            agent_id="gcode-opt", project_id=project_id, notifier=notifier,
            role=AgentRole.WORKER, context_limit_kb=kwargs.get("context_limit_kb", 15.0),
            context_file=kwargs.get("context_file"),
        )
        self.working_dir = Path(working_dir or PRINTER_DIR)

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]
        handler = {
            "optimize": self._optimize,
            "generate_calibration": self._generate_calibration,
            "analyze_gcode": self._analyze_gcode,
            "fix_temperatures": self._fix_temperatures,
            "inject_bed_mesh": self._inject_bed_mesh,
            "set_pressure_advance": self._set_pressure_advance,
            "optimize_paths": self._optimize_paths,
            "estimate_time": self._estimate_time,
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

    def _run_python(self, script: str, args: Optional[list] = None) -> dict:
        script_path = self.working_dir / script
        if not script_path.exists():
            return {"status": "error", "error": f"Script nao encontrado: {script_path}"}
        cmd = [sys.executable, str(script_path)] + (args or [])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=self.working_dir)
            return {"status": "ok" if result.returncode == 0 else "error", "stdout": result.stdout[-3000:], "stderr": result.stderr[-1000:], "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Timeout apos 120s"}

    def _optimize(self, task: dict) -> dict:
        path = task.get("gcode_path", "")
        if not path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        return self._run_python("gcode_optimizer.py", [path])

    def _generate_calibration(self, task: dict) -> dict:
        gtype = task.get("type", "cube")
        if gtype == "cube":
            return self._run_python("gen_cube_gcode.py")
        return {"status": "error", "error": f"Tipo desconhecido: {gtype}. Tipos: cube"}

    def _analyze_gcode(self, task: dict) -> dict:
        path = task.get("gcode_path", "")
        if not path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        full_path = self.working_dir / path
        if not full_path.exists():
            return {"status": "error", "error": f"Arquivo nao encontrado: {full_path}"}
        with open(full_path, "r") as f:
            content = f.read()
        lines = content.split("\n")
        layers = sum(1 for l in lines if l.startswith("; LAYER") or l.startswith(";LAYER"))
        e_moves = sum(1 for l in lines if "G1" in l and "E" in l and ";" not in l.split("E")[0][-2:])
        travels = sum(1 for l in lines if "G0" in l or ("G1" in l and "E" not in l))
        total_e = 0
        for l in lines:
            if "G1" in l and "E" in l:
                m = [x for x in l.split() if x.startswith("E")]
                if m:
                    try:
                        total_e = float(m[-1][1:])
                    except:
                        pass
        return {
            "status": "ok",
            "analysis": {
                "total_lines": len(lines),
                "layers": layers,
                "extrusion_moves": e_moves,
                "travel_moves": travels,
                "total_extrusion_mm": round(total_e, 2),
                "file_size_kb": round(full_path.stat().st_size / 1024, 1),
            }
        }

    def _fix_temperatures(self, task: dict) -> dict:
        return self._run_python("gcode_optimizer.py", ["--fix-temps", task["gcode_path"]])

    def _inject_bed_mesh(self, task: dict) -> dict:
        path = task.get("gcode_path", "")
        if not path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        full_path = self.working_dir / path
        if not full_path.exists():
            return {"status": "error", "error": f"Arquivo nao encontrado: {full_path}"}
        with open(full_path, "r+") as f:
            content = f.read()
            content = content.replace("G28 ;Home", "G28 ;Home\nBED_MESH_CALIBRATE\nSET_PRESSURE_ADVANCE ADVANCE=0.03")
            content = content.replace("G28\n", "G28\nBED_MESH_CALIBRATE\nSET_PRESSURE_ADVANCE ADVANCE=0.03\n")
            f.seek(0)
            f.write(content)
            f.truncate()
        return {"status": "ok", "message": "BED_MESH_CALIBRATE + PA 0.03 injetados"}

    def _set_pressure_advance(self, task: dict) -> dict:
        path = task.get("gcode_path", "")
        pa = task.get("pa_value", 0.03)
        if not path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        full_path = self.working_dir / path
        with open(full_path, "r+") as f:
            content = f.read()
            content = content.replace("SET_PRESSURE_ADVANCE ADVANCE=0.030", f"SET_PRESSURE_ADVANCE ADVANCE={pa}")
            f.seek(0)
            f.write(content)
            f.truncate()
        return {"status": "ok", "pa": pa}

    def _optimize_paths(self, task: dict) -> dict:
        return self._run_python("gcode_optimizer.py", ["--optimize-paths", task["gcode_path"]])

    def _estimate_time(self, task: dict) -> dict:
        path = task.get("gcode_path", "")
        if not path:
            return {"status": "error", "error": "gcode_path nao fornecido"}
        full_path = self.working_dir / path
        if not full_path.exists():
            return {"status": "error", "error": f"Arquivo nao encontrado: {full_path}"}
        with open(full_path) as f:
            content = f.read()
        # Estimate: count total extrusion distance, assume 60mm/s avg
        total_e = 0
        for line in content.split("\n"):
            if "G1" in line and "E" in line:
                parts = line.split()
                for p in parts:
                    if p.startswith("E"):
                        try:
                            total_e = abs(float(p[1:]))
                        except:
                            pass
        est_minutes = total_e / 60 * 3  # rough estimate
        return {"status": "ok", "estimated_minutes": round(est_minutes, 1), "estimated_human": f"{int(est_minutes//60)}h{int(est_minutes%60)}m"}

    def _run_script(self, task: dict) -> dict:
        return self._run_python(task["script"], task.get("args"))

    def _get_capabilities(self) -> dict:
        return {"agent_id": self.agent_id, "role": self.role.value, "actions": self.ACTIONS}
