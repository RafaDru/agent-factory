"""
Agent Factory — Agente de Desenvolvimento da Factory (REAL)
============================================================
Opera arquivos reais: ler, escrever, editar, rodar scripts/testes/git.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.agents.base import AgentBase, AgentRole, StructuredError
from src.protocols.events import EventNotifier


class AgentFactoryDevAgent(AgentBase):
    """
    Agente de Desenvolvimento do Agent Factory.
    Acoes reais: leitura/escrita de arquivos, execucao de scripts/testes/git.
    """

    ACTIONS = {
        "read_file": {
            "description": "Le conteudo de um arquivo",
            "params": {"file_path": "str (obrigatorio) - caminho absoluto"},
        },
        "write_file": {
            "description": "Escreve conteudo em um arquivo (cria diretorios se necessario)",
            "params": {"file_path": "str (obrigatorio)", "content": "str (obrigatorio)"},
        },
        "edit_file": {
            "description": "Substitui texto em um arquivo existente",
            "params": {"file_path": "str (obrigatorio)", "old_string": "str (obrigatorio)", "new_string": "str (obrigatorio)"},
        },
        "run_script": {
            "description": "Executa um script Python via subprocess",
            "params": {"script_path": "str (obrigatorio)", "args": "list[str] (opcional)", "timeout": "int (opcional, padrao 300)"},
        },
        "run_tests": {
            "description": "Executa pytest em um diretorio/arquivo",
            "params": {"path": "str (opcional, padrao tests/)", "args": "list[str] (opcional)"},
        },
        "run_git": {
            "description": "Executa comando git",
            "params": {"args": "list[str] (obrigatorio, ex: ['add', '.'])", "workdir": "str (opcional)"},
        },
        "list_directory": {
            "description": "Lista conteudo de um diretorio",
            "params": {"path": "str (obrigatorio)", "pattern": "str (opcional, ex: *.py)"},
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
            agent_id="agent-factory-dev",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
            context_limit_kb=kwargs.get("context_limit_kb", 15.0),
            context_file=kwargs.get("context_file"),
        )
        self.working_dir = Path(working_dir or os.getcwd())

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]

        if action == "read_file":
            return self._read_file(task)
        elif action == "write_file":
            return self._write_file(task)
        elif action == "edit_file":
            return self._edit_file(task)
        elif action == "run_script":
            return self._run_script(task)
        elif action == "run_tests":
            return self._run_tests(task)
        elif action == "run_git":
            return self._run_git(task)
        elif action == "list_directory":
            return self._list_directory(task)
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
                hint=f"Use uma das acoes disponiveis ou chame action=get_capabilities para detalhes.",
            )

    def _read_file(self, task: dict) -> dict:
        file_path = Path(task["file_path"])
        if not file_path.exists():
            return {"status": "error", "error": f"Arquivo não encontrado: {file_path}"}
        try:
            content = file_path.read_text(encoding="utf-8")
            return {
                "status": "ok",
                "file_path": str(file_path),
                "content": content,
                "size_bytes": len(content.encode("utf-8")),
                "line_count": content.count("\n") + 1,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _write_file(self, task: dict) -> dict:
        file_path = Path(task["file_path"])
        content = task.get("content", "")
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return {
                "status": "ok",
                "file_path": str(file_path),
                "size_bytes": len(content.encode("utf-8")),
                "line_count": content.count("\n") + 1,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _edit_file(self, task: dict) -> dict:
        file_path = Path(task["file_path"])
        old_string = task.get("old_string", "")
        new_string = task.get("new_string", "")
        if not file_path.exists():
            return {"status": "error", "error": f"Arquivo não encontrado: {file_path}"}
        try:
            content = file_path.read_text(encoding="utf-8")
            if old_string not in content:
                return {
                    "status": "error",
                    "error": "old_string não encontrado no arquivo",
                }
            occurrences = content.count(old_string)
            if occurrences > 1:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string)
            file_path.write_text(new_content, encoding="utf-8")
            return {
                "status": "ok",
                "file_path": str(file_path),
                "replacements": occurrences,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_script(self, task: dict) -> dict:
        script_path = task.get("script_path", "")
        args = task.get("args", [])
        timeout = task.get("timeout", 300)

        script = Path(script_path)
        if not script.exists():
            return {"status": "error", "error": f"Script não encontrado: {script_path}"}

        cmd = [sys.executable, str(script)] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_dir,
            )
            return {
                "status": "ok",
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": f"Timeout após {timeout}s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_tests(self, task: dict) -> dict:
        test_path = task.get("path", "tests/")
        args = task.get("args", [])

        cmd = [sys.executable, "-m", "pytest", str(test_path), "-v"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.working_dir,
            )
            return {
                "status": "ok",
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-1000:],
                "returncode": result.returncode,
                "passed": result.returncode == 0,
                "summary": self._parse_test_summary(result.stdout),
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Timeout após 120s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_test_summary(self, output: str) -> dict:
        passed = failed = errors = 0
        for line in output.split("\n"):
            if "passed" in line and "failed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i - 1]) if i > 0 else 0
                    elif p == "failed":
                        failed = int(parts[i - 1]) if i > 0 else 0
                    elif p == "error":
                        errors = int(parts[i - 1]) if i > 0 else 0
        return {"passed": passed, "failed": failed, "errors": errors}

    def _run_git(self, task: dict) -> dict:
        git_args = task.get("args", [])
        workdir = Path(task.get("workdir", str(self.working_dir)))

        cmd = ["git"] + list(git_args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workdir,
            )
            return {
                "status": "ok",
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-1000:],
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _list_directory(self, task: dict) -> dict:
        path = Path(task.get("path", str(self.working_dir)))
        pattern = task.get("pattern", "*")

        if not path.exists():
            return {"status": "error", "error": f"Diretório não encontrado: {path}"}

        items = []
        for p in path.glob(pattern):
            items.append({
                "name": p.name,
                "path": str(p),
                "type": "dir" if p.is_dir() else "file",
                "size": p.stat().st_size if p.is_file() else 0,
            })

        return {
            "status": "ok",
            "path": str(path),
            "items": sorted(items, key=lambda x: (x["type"] != "dir", x["name"])),
            "total": len(items),
        }

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "working_dir": str(self.working_dir),
            "actions": self.ACTIONS,
        }
