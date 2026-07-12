"""
Agent Factory — Agente de QA (REAL)
=====================================
Executa testes, linters e validacoes em codigo real.
"""

import sys
import subprocess
import traceback
from pathlib import Path
from typing import Any, Optional

from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput
from src.protocols.events import EventNotifier

class QAAgent(StandardBaseAgent):
    """
    Agente de Qualidade — validacao real de artefatos.
    """

    ACTIONS = {
        "run_tests": {"description": "Executa pytest e retorna resultados", "params": {"path": "str", "args": "list[str] (opcional)"}},
        "validate_python_syntax": {"description": "Valida sintaxe Python de um arquivo", "params": {"file_path": "str"}},
        "analyze_artifact": {"description": "Le um artefato do disco e avalia seu conteudo", "params": {"file_path": "str", "checks": "list[str] (opcional)"}},
        "lint": {"description": "Executa flake8 ou pycodestyle em um arquivo/diretorio", "params": {"path": "str"}},
        "file_exists": {"description": "Verifica se arquivo existe e nao esta vazio", "params": {"file_path": "str"}},
    }

    def __init__(self, project_id: str, notifier: EventNotifier, **kwargs):
        super().__init__(
            agent_id="qa",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
            **kwargs,
        )
        self.working_dir = Path(kwargs.get("working_dir", Path.cwd()))

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.working_dir / p).resolve()

    def execute(self, task: dict[str, Any]) -> TaskOutput:
        action = task.get("action")
        aliases = {
            "check_file_exists": "file_exists", "verify_file": "file_exists",
            "validate_file": "analyze_artifact", "check_content": "analyze_artifact",
            "validate_syntax": "validate_python_syntax",
            "get_capabilities": "get_capabilities",
        }
        resolved = aliases.get(action, action)

        handlers = {
            "run_tests": self._run_tests,
            "validate_python_syntax": self._validate_python_syntax,
            "analyze_artifact": self._analyze_artifact,
            "lint": self._lint,
            "file_exists": self._file_exists,
            "get_capabilities": lambda t: TaskOutput.success(summary="Capabilities", capabilities=self.get_capabilities()),
        }
        handler = handlers.get(resolved)
        if handler:
            return handler(task)

        available = sorted(self.ACTIONS.keys())
        return TaskOutput.needs_direction(
            rationale=f"Acao desconhecida: '{action}'. Disponiveis: {available}",
            available_actions=available,
        )

    def _run_tests(self, task: dict) -> TaskOutput:
        test_path = task.get("path", "tests/")
        args = task.get("args", ["--tb=short", "-q"])
        cmd = [sys.executable, "-m", "pytest", test_path] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=self.working_dir)
            passed = result.returncode == 0
            cls = TaskOutput.success if passed else TaskOutput.failure
            return cls(
                summary=f"Testes {'passaram' if passed else 'falharam'} (codigo {result.returncode})",
                rationale=result.stdout[-500:],
                returncode=result.returncode, passed=passed,
            )
        except subprocess.TimeoutExpired:
            return TaskOutput.failure(rationale="Testes excederam timeout de 300s")
        except FileNotFoundError:
            return TaskOutput.failure(rationale="pytest nao encontrado. Instale com: pip install pytest")
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao executar testes: {e}")

    def _validate_python_syntax(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Parametro 'file_path' ausente.",
                available_actions=["list_directory", "file_exists"],
            )
        path = self._resolve(file_path)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            return TaskOutput.success(
                summary="Sintaxe Python valida",
                path=str(path), valid=True,
            )
        except SyntaxError as e:
            return TaskOutput.failure(
                rationale=f"Erro de sintaxe na linha {e.lineno}: {e.msg}",
                path=str(path), valid=False, lineno=e.lineno,
            )
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao validar: {e}")

    def _analyze_artifact(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Parametro 'file_path' ausente. Informe caminho do artefato.",
                available_actions=["file_exists", "list_directory"],
            )
        path = self._resolve(file_path)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Artefato nao encontrado: {path}")

        content = path.read_text(encoding="utf-8", errors="replace")
        checks = task.get("checks", ["exists", "non_empty"])
        results = {}

        for check in checks:
            if check == "exists":
                results["exists"] = True
            elif check == "non_empty":
                results["non_empty"] = len(content.strip()) > 0
            elif check == "min_length":
                results["min_length"] = len(content) >= task.get("min_length", 50)
            elif check == "contains":
                kw = task.get("keyword", "")
                results[f"contains:{kw}"] = kw in content

        passed = all(results.values()) if results else True
        cls = TaskOutput.success if passed else TaskOutput.failure
        return cls(
            summary=f"Artefato {path.name}: {len(results)} checks, {'todos ok' if passed else 'alguns falharam'}",
            rationale=str(results),
            path=str(path), size_bytes=len(content.encode("utf-8")),
            lines=content.count("\n") + 1, checks=results, all_passed=passed,
        )

    def _lint(self, task: dict) -> TaskOutput:
        target_path = self._resolve(task.get("path", ""))
        if not target_path or not target_path.exists():
            return TaskOutput.failure(rationale=f"Caminho nao encontrado: {target_path}")

        for tool in ["flake8", "pycodestyle", "pylint"]:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", tool, str(target_path)],
                    capture_output=True, text=True, timeout=60, cwd=self.working_dir,
                )
                issues = [l for l in result.stdout.split("\n") if l.strip() and ":" in l]
                if result.returncode == 0:
                    return TaskOutput.success(summary=f"{tool}: sem issues", tool=tool, path=str(target_path))
                return TaskOutput.partial(
                    summary=f"{tool}: {len(issues)} issues encontradas",
                    rationale=result.stdout[:500],
                    tool=tool, path=str(target_path), issues=issues[:50], issue_count=len(issues),
                )
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue

        return TaskOutput.success(
            summary="Nenhum liner instalado, validacao basica aplicada",
            note="Instale flake8/pycodestyle/pylint para analise detalhada",
            path=str(target_path), issues=[],
        )

    def _file_exists(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Parametro 'file_path' ausente. Informe qual arquivo verificar.",
                available_actions=["list_directory"],
            )
        path = self._resolve(file_path)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return TaskOutput.success(
            summary=f"Arquivo {path.name}: {len(content.encode('utf-8'))} bytes, {content.count(chr(10))+1} linhas",
            path=str(path), exists=True,
            size_bytes=len(content.encode("utf-8")),
            lines=content.count("\n") + 1, non_empty=len(content.strip()) > 0,
        )
