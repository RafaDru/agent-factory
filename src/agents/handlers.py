"""Handlers compartilhados para workers declarativos criados pelo AgentFactory."""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.protocols.schema import TaskOutput, OutputStatus


def _resolve(self, path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    wd = Path(getattr(self, 'working_dir', os.getcwd()))
    return (wd / p).resolve()


def read_file(self, task: dict[str, Any]) -> TaskOutput:
    file_path = task.get("file_path") or task.get("path")
    if not file_path:
        return TaskOutput.needs_direction(rationale="Informe file_path.", available_actions=["list_directory"])
    path = _resolve(self, file_path)
    if not path.exists():
        return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}", file_path=str(path))
    try:
        content = path.read_text(encoding="utf-8")
        return TaskOutput.success(summary=f"Lido: {path}", rationale=f"Conteudo lido ({len(content)} chars)", path=str(path), size=len(content))
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao ler {path}: {e}")


def write_file(self, task: dict[str, Any]) -> TaskOutput:
    file_path = task.get("file_path") or task.get("path")
    content = task.get("content")
    if not file_path:
        return TaskOutput.needs_direction(rationale="Informe file_path.")
    if content is None:
        return TaskOutput.needs_direction(rationale="Informe content.")
    path = _resolve(self, file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return TaskOutput.success(summary=f"Escrito: {path}", rationale=f"Conteudo escrito ({len(content)} chars)", path=str(path), size=len(content))
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao escrever {path}: {e}")


def edit_file(self, task: dict[str, Any]) -> TaskOutput:
    file_path = task.get("file_path") or task.get("path")
    old = task.get("old_string")
    new = task.get("new_string")
    if not file_path or old is None or new is None:
        return TaskOutput.needs_direction(rationale="Informe file_path, old_string e new_string.")
    path = _resolve(self, file_path)
    if not path.exists():
        return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
    try:
        content = path.read_text(encoding="utf-8")
        if old not in content:
            return TaskOutput.failure(rationale=f"Texto nao encontrado em {path}", snippet=old[:80])
        changes = content.count(old)
        new_content = content.replace(old, new, 1) if changes == 1 else content.replace(old, new)
        path.write_text(new_content, encoding="utf-8")
        return TaskOutput.success(summary=f"Editado: {path}", rationale=f"{changes} ocorrencia(s) alterada(s)", path=str(path), changes=changes)
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao editar {path}: {e}")


def list_directory(self, task: dict[str, Any]) -> TaskOutput:
    path_str = task.get("path", ".")
    pattern = task.get("pattern")
    path = _resolve(self, path_str)
    if not path.exists():
        return TaskOutput.failure(rationale=f"Diretorio nao encontrado: {path}")
    try:
        if pattern:
            matches = [str(p.relative_to(path)) for p in sorted(path.rglob(pattern))]
        else:
            matches = [str(p.relative_to(path)) for p in sorted(path.iterdir())]
        return TaskOutput.success(summary=f"Listado: {path} ({len(matches)} itens)", files=matches, path=str(path))
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao listar {path}: {e}")


def run_script(self, task: dict[str, Any]) -> TaskOutput:
    script_path = task.get("script_path")
    args = task.get("args", [])
    if not script_path:
        return TaskOutput.needs_direction(rationale="Informe script_path.")
    path = _resolve(self, script_path)
    if not path.exists():
        return TaskOutput.failure(rationale=f"Script nao encontrado: {path}")
    try:
        cmd = [sys.executable, str(path)] + list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return TaskOutput.success(summary=f"Script executado: {path}", stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)
    except subprocess.TimeoutExpired:
        return TaskOutput.failure(rationale=f"Script excedeu 120s: {path}")
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao executar {path}: {e}")


def run_tests(self, task: dict[str, Any]) -> TaskOutput:
    path = task.get("path", "tests/")
    args = task.get("args", ["-v"])
    try:
        cmd = [sys.executable, "-m", "pytest", str(path)] + list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        failed = r.returncode != 0
        status = OutputStatus.FAILURE if failed else OutputStatus.SUCCESS
        return TaskOutput(
            status=status,
            summary=f"Testes: {'FALHARAM' if failed else 'PASSARAM'}",
            details={"stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode},
        )
    except subprocess.TimeoutExpired:
        return TaskOutput.failure(rationale="Testes excederam 300s")
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao executar testes: {e}")


def run_git(self, task: dict[str, Any]) -> TaskOutput:
    args = task.get("args", [])
    if not args:
        return TaskOutput.needs_direction(rationale="Informe args para git.")
    try:
        cmd = ["git"] + list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return TaskOutput.success(summary=f"git {' '.join(args)}", stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)
    except subprocess.TimeoutExpired:
        return TaskOutput.failure(rationale="git excedeu 60s")
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro no git: {e}")


def lint(self, task: dict[str, Any]) -> TaskOutput:
    path = task.get("path", "src/")
    fix = task.get("fix", False)
    try:
        cmd = [sys.executable, "-m", "ruff", "check", str(path)]
        if fix:
            cmd.append("--fix")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return TaskOutput.success(summary=f"Lint: {path}", stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro no lint: {e}")


def type_check(self, task: dict[str, Any]) -> TaskOutput:
    path = task.get("path", "src/")
    try:
        r = subprocess.run(["pyright", str(path)], capture_output=True, text=True, timeout=120)
        return TaskOutput.success(summary=f"Type check: {path}", stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro no type check: {e}")


def validate_python_syntax(self, task: dict[str, Any]) -> TaskOutput:
    file_path = task.get("file_path")
    if not file_path:
        return TaskOutput.needs_direction(rationale="Informe file_path.")
    path = _resolve(self, file_path)
    if not path.exists():
        return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
    try:
        import ast
        ast.parse(path.read_text(encoding="utf-8"))
        return TaskOutput.success(summary=f"Syntax OK: {path}")
    except SyntaxError as e:
        return TaskOutput.failure(rationale=f"Erro de sintaxe: {e}", line=e.lineno, offset=e.offset)
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao validar: {e}")


def rename_file(self, task: dict[str, Any]) -> TaskOutput:
    src = task.get("src") or task.get("file_path")
    dst = task.get("dst")
    if not src or not dst:
        return TaskOutput.needs_direction(rationale="Informe src e dst.")
    src_path = _resolve(self, src)
    dst_path = _resolve(self, dst)
    try:
        src_path.rename(dst_path)
        return TaskOutput.success(summary=f"Renomeado: {src} -> {dst}")
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao renomear: {e}")


def delete_file(self, task: dict[str, Any]) -> TaskOutput:
    file_path = task.get("file_path") or task.get("path")
    if not file_path:
        return TaskOutput.needs_direction(rationale="Informe file_path.")
    path = _resolve(self, file_path)
    if not path.exists():
        return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
    try:
        if path.is_dir():
            import shutil; shutil.rmtree(path)
        else:
            path.unlink()
        return TaskOutput.success(summary=f"Removido: {path}")
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao remover: {e}")


import sys


_WHITELIST = {"gh", "python", "pip", "npm", "npx", "dir", "type", "git"}


def run_command(self, task: dict[str, Any]) -> TaskOutput:
    command = task.get("command", "")
    args = task.get("args", [])
    if command not in _WHITELIST:
        return TaskOutput.failure(rationale=f"Comando nao autorizado: {command}. Whitelist: {sorted(_WHITELIST)}")
    try:
        cmd = [command] + list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return TaskOutput.success(summary=f"Comando executado: {command}", stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)
    except subprocess.TimeoutExpired:
        return TaskOutput.failure(rationale=f"Comando excedeu 120s: {command}")
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao executar {command}: {e}")


def file_exists(self, task: dict[str, Any]) -> TaskOutput:
    file_path = task.get("file_path")
    if not file_path:
        return TaskOutput.needs_direction(rationale="Informe file_path.")
    path = _resolve(self, file_path)
    return TaskOutput.success(summary=f"Arquivo {'existe' if path.exists() else 'nao existe'}: {path}", path=str(path), exists=path.exists())
