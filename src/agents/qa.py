"""
Agent Factory — Agente de QA (REAL)
=====================================
Executa testes, linters e validacoes em código real.
"""

import sys
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.agents.base import AgentBase, AgentRole, StructuredError
from src.protocols.events import EventNotifier


class QAAgent(AgentBase):
    """
    Agente de Qualidade.
    Acoes reais: pytest, ruff, pyright, validacao de imports.
    """

    ACTIONS = {
        "run_tests": {
            "description": "Executa pytest em diretorio/arquivo especifico",
            "params": {"path": "str (opcional, padrao tests/)", "args": "list[str] (opcional, ex: ['-x', '--tb=short'])"},
        },
        "lint": {
            "description": "Executa ruff check em diretorio/arquivo",
            "params": {"path": "str (obrigatorio)", "fix": "bool (opcional, padrao false)"},
        },
        "type_check": {
            "description": "Executa pyright para checagem de tipos",
            "params": {"path": "str (obrigatorio)"},
        },
        "validate_python_syntax": {
            "description": "Valida sintaxe Python de um arquivo",
            "params": {"file_path": "str (obrigatorio)"},
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
        self.working_dir = Path(working_dir or Path.cwd())

    def validate_input(self, task: dict[str, Any]) -> bool:
        return "action" in task

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]

        if action == "run_tests":
            return self._run_tests(task)
        elif action == "lint":
            return self._lint(task)
        elif action == "type_check":
            return self._type_check(task)
        elif action == "validate_python_syntax":
            return self._validate_python_syntax(task)
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
                hint=f"Use action=get_capabilities para lista completa com parametros.",
            )

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
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-2000:],
                "returncode": result.returncode,
                "passed": result.returncode == 0,
                "summary": self._parse_test_summary(result.stdout),
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Timeout apos 120s"}
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

    def _lint(self, task: dict) -> dict:
        lint_path = task.get("path", ".")
        fix = task.get("fix", False)

        cmd = [sys.executable, "-m", "ruff", "check", str(lint_path)]
        if fix:
            cmd.append("--fix")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.working_dir,
            )
            issues = []
            for line in result.stdout.split("\n"):
                if line.strip() and (".py:" in line or "error" in line.lower()):
                    issues.append(line.strip())

            return {
                "status": "ok",
                "issues_count": len(issues),
                "issues": issues[:50],
                "total_lines": len(result.stdout.split("\n")),
                "fix_applied": fix,
                "passed": result.returncode == 0,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _type_check(self, task: dict) -> dict:
        check_path = task.get("path", ".")

        cmd = [sys.executable, "-m", "pyright", str(check_path)]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.working_dir,
            )
            return {
                "status": "ok",
                "stdout": result.stdout[-3000:],
                "returncode": result.returncode,
                "passed": result.returncode == 0,
            }
        except FileNotFoundError:
            return {
                "status": "warning",
                "message": "pyright nao encontrado. Instale com: npm install -g pyright",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _validate_python_syntax(self, task: dict) -> dict:
        file_path = Path(task.get("file_path", ""))
        if not file_path.exists():
            return {"status": "error", "error": f"Arquivo nao encontrado: {file_path}"}

        try:
            compile(file_path.read_text(encoding="utf-8"), str(file_path), "exec")
            return {
                "status": "ok",
                "file_path": str(file_path),
                "valid": True,
            }
        except SyntaxError as e:
            return {
                "status": "ok",
                "file_path": str(file_path),
                "valid": False,
                "error": f"Erro de sintaxe: {e}",
            }

    def _get_capabilities(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "working_dir": str(self.working_dir),
            "actions": self.ACTIONS,
        }
