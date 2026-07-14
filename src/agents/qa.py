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

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "run_tests": {"description": "Executa pytest e retorna resultados", "params": {"path": "str", "args": "list[str] (opcional)"}},
        "validate_python_syntax": {"description": "Valida sintaxe Python de um arquivo", "params": {"file_path": "str"}},
        "analyze_artifact": {"description": "Le um artefato do disco e avalia seu conteudo", "params": {"file_path": "str", "checks": "list[str] (opcional)"}},
        "lint": {"description": "Executa flake8 ou pycodestyle em um arquivo/diretorio", "params": {"path": "str"}},
        "file_exists": {"description": "Verifica se arquivo existe e nao esta vazio", "params": {"file_path": "str"}},
        "review_code": {"description": "Usa LLM para revisar codigo (boas praticas, seguranca, qualidade)", "params": {"file_path": "str"}},
        "suggest_fixes": {"description": "Usa LLM para analisar falhas e sugerir correcoes", "params": {"error": "str - descricao do erro/falha", "file_path": "str (opcional)"}},
        "analyze_project": {"description": "Usa LLM para analisar saude geral do projeto", "params": {"path": "str (opcional)"}},
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
            "review_code": self._review_code_with_llm,
            "suggest_fixes": self._suggest_fixes_with_llm,
            "analyze_project": self._analyze_project_with_llm,
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

    def _build_context_prompt(self, task: dict) -> str:
        """Carrega os 3 niveis de contexto se disponiveis e retorna como prefixo do prompt."""
        parts = []
        ctx_global = self.load_global_context()
        if ctx_global:
            parts.append(f"## Contexto Global do Projeto\n\n{ctx_global}")
        mission_id = task.get("_mission_id", "")
        if mission_id:
            ctx_mission = self.load_mission_context(mission_id)
            if ctx_mission:
                parts.append(f"## Contexto da Missão\n\n{ctx_mission}")
            task_id = task.get("_task_id", "")
            if task_id and self.agent_id:
                ctx_task = self.load_task_context(mission_id, task_id, self.agent_id)
                if ctx_task:
                    parts.append(f"## Contexto desta Tarefa\n\n{ctx_task}")
        dep_ctx = task.get("_dependency_context", "")
        if dep_ctx:
            parts.append(dep_ctx)
        return "\n\n".join(parts)

    def _save_artifact(self, task: dict, name: str, content: str):
        """Salva artefato se a task tiver contexto de missao."""
        mid = task.get("_mission_id", "")
        tid = task.get("_task_id", "")
        if mid and tid:
            self.save_task_artifact(mid, tid, self.agent_id, name, content)

    def _review_code_with_llm(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Informe file_path para revisar.",
                available_actions=["list_directory"],
            )
        path = self._resolve(file_path)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")

        if path.is_dir():
            files = [str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()]
            return TaskOutput.failure(
                rationale=f"review_code exige arquivo, mas recebeu diretorio: {path}. "
                          f"Arquivos encontrados: {files[:10]}. "
                          f"Use analyze_project para revisar o diretorio todo, "
                          f"ou analyze_artifact para artefatos de design.",
                available_actions=["analyze_project", "analyze_artifact", "list_directory"],
            )

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao ler {path}: {e}")

        context_prefix = self._build_context_prompt(task)
        prompt = f"""{context_prefix}

Revise o seguinte codigo e forneça uma analise completa:

```{path.suffix[1:] if path.suffix else ''}
{content[:8000]}
```

Analise: boas praticas, seguranca, desempenho, legibilidade, possiveis bugs.
Forneça uma nota de 0-10 e sugestoes especificas de melhoria."""
        system_prompt = "Voce e um revisor de codigo sênior. Seja critico e construtivo."
        llm_response = self._llm_think(prompt, system_prompt=system_prompt, max_tokens=2048)

        if llm_response:
            self._save_artifact(task, "review_analise.md", llm_response)
            return TaskOutput.success(
                summary=f"Revisao concluida para {path.name}",
                rationale="Codigo analisado via LLM",
                file_path=str(path), review=llm_response,
            )
        return TaskOutput.failure(
            rationale="LLM nao disponivel para revisao. Use analise manual.",
            available_actions=["analyze_artifact", "lint", "validate_python_syntax"],
        )

    def _suggest_fixes_with_llm(self, task: dict) -> TaskOutput:
        error_desc = task.get("error") or task.get("description", "")
        if not error_desc:
            return TaskOutput.needs_direction(
                rationale="Descreva o erro no campo 'error' para sugerir correcoes.",
                available_actions=["run_tests", "lint"],
            )
        file_path = task.get("file_path", "")

        context = ""
        if file_path:
            path = self._resolve(file_path)
            if path.exists():
                try:
                    context = f"\n\nConteudo do arquivo:\n```\n{path.read_text(encoding='utf-8')[:4000]}\n```"
                except Exception:
                    pass

        ctx_prefix = self._build_context_prompt(task)
        prompt = f"""{ctx_prefix}

Analise o seguinte erro e sugira correcoes:

ERRO: {error_desc}{context}

Forneça: causa raiz, solucao proposta e codigo corrigido se aplicavel."""
        system_prompt = "Voce e um engenheiro de software focado em debugging. Seja preciso e objetivo."
        llm_response = self._llm_think(prompt, system_prompt=system_prompt, max_tokens=2048)

        if llm_response:
            self._save_artifact(task, "sugestoes_correcao.md", llm_response)
            return TaskOutput.success(
                summary="Sugestoes de correcao geradas via LLM",
                rationale=f"LLM: {self._llm.__class__.__name__ if self._llm else 'N/A'}",
                error=error_desc, suggestions=llm_response,
            )
        return TaskOutput.failure(
            rationale="LLM nao disponivel para sugerir correcoes.",
            available_actions=["run_tests", "lint", "analyze_artifact"],
        )

    def _analyze_project_with_llm(self, task: dict) -> TaskOutput:
        base_path = self._resolve(task.get("path", "."))
        if not base_path.exists():
            return TaskOutput.failure(rationale=f"Diretorio nao encontrado: {base_path}")

        files = list(base_path.rglob("*.py"))[:30]
        file_list = "\n".join(str(f.relative_to(self.working_dir)) for f in files)
        total = len(files)

        ctx_prefix = self._build_context_prompt(task)
        prompt = f"""{ctx_prefix}

Analise a saude do projeto em {base_path}:

Arquivos Python encontrados: {total}
Primeiros {min(total, 30)} arquivos:
{file_list}

Forneça: estrutura geral, pontos fortes, riscos potenciais, sugestoes de melhoria."""
        system_prompt = "Voce e um arquiteto de software especializado em analise de projetos."
        llm_response = self._llm_think(prompt, system_prompt=system_prompt, max_tokens=2048)

        if llm_response:
            self._save_artifact(task, "analise_projeto.md", llm_response)
            return TaskOutput.success(
                summary=f"Analise de projeto concluida: {total} arquivos Python",
                rationale=f"LLM: {self._llm.__class__.__name__ if self._llm else 'N/A'}",
                path=str(base_path), total_files=total, analysis=llm_response,
            )
        return TaskOutput.failure(
            rationale="LLM nao disponivel para analise de projeto.",
            available_actions=["run_tests", "lint"],
        )
