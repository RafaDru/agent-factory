"""
Agent Factory — Agente de Desenvolvimento da Factory (REAL)
============================================================
Opera arquivos reais: ler, escrever, editar, rodar scripts/testes/git.
"""

import os
import sys
import subprocess
import traceback
from pathlib import Path
from typing import Any, Optional

from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput, OutputStatus
from src.protocols.events import EventNotifier

class AgentFactoryDevAgent(StandardBaseAgent):
    """
    Agente de Desenvolvimento do Agent Factory.
    """

    _DEFAULT_LLM = "auto"

    ACTIONS = {
        "read_file": {"description": "Le conteudo de um arquivo", "params": {"file_path": "str"}},
        "write_file": {"description": "Escreve conteudo em um arquivo", "params": {"file_path": "str", "content": "str"}},
        "edit_file": {"description": "Edita um arquivo (substitui trecho)", "params": {"file_path": "str", "old_string": "str", "new_string": "str"}},
        "list_directory": {"description": "Lista arquivos em um diretorio com glob", "params": {"path": "str", "pattern": "str"}},
        "run_script": {"description": "Executa script Python", "params": {"script_path": "str", "args": "list[str] (opcional)"}},
        "run_tests": {"description": "Executa pytest", "params": {"path": "str", "args": "list[str] (opcional)"}},
        "run_git": {"description": "Executa comando git", "params": {"args": "list[str]"}},
        "rename_file": {"description": "Renomeia ou move um arquivo", "params": {"src": "str", "dst": "str"}},
        "delete_file": {"description": "Remove um arquivo", "params": {"file_path": "str"}},
        "generate_code": {"description": "Gera codigo via LLM (React, Python, etc)", "params": {"spec": "str - especificacao do que gerar", "language": "str (opcional)", "output_path": "str (opcional)"}},
        "implement_feature": {"description": "Usa LLM para planejar e implementar uma feature", "params": {"spec": "str - descricao da feature", "output_path": "str (opcional)"}},
        "refactor_code": {"description": "Usa LLM para analisar e refatorar codigo existente", "params": {"file_path": "str", "instructions": "str (opcional)"}},
    }

    def __init__(self, project_id: str, notifier: EventNotifier, **kwargs):
        super().__init__(
            agent_id="dev",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
            **kwargs,
        )
        self.working_dir = Path(kwargs.get("working_dir", os.getcwd()))

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.working_dir / p).resolve()

    def execute(self, task: dict[str, Any]) -> TaskOutput:
        action = task.get("action")
        aliases = {
            "create_file": "write_file", "create": "write_file", "make_file": "write_file",
            "write": "write_file", "read": "read_file",
            "list_files": "list_directory", "list": "list_directory",
            "edit": "edit_file", "rename": "rename_file",
            "delete": "delete_file", "remove_file": "delete_file", "move_file": "rename_file",
            "run": "run_script", "execute_script": "run_script",
            "test": "run_tests", "pytest": "run_tests", "git": "run_git",
        }
        action = aliases.get(action, action)

        handlers = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "edit_file": self._edit_file,
            "list_directory": self._list_directory,
            "run_script": self._run_script,
            "run_tests": self._run_tests,
            "run_git": self._run_git,
            "rename_file": self._rename_file,
            "delete_file": self._delete_file,
            "generate_code": self._generate_code_with_llm,
            "implement_feature": self._implement_feature_with_llm,
            "refactor_code": self._refactor_code_with_llm,
            "get_capabilities": lambda t: TaskOutput.success(summary="Capabilities", capabilities=self.get_capabilities()),
        }

        handler = handlers.get(action)
        if handler:
            return handler(task)

        available = sorted(self.ACTIONS.keys())
        return TaskOutput.needs_direction(
            rationale=f"Acao desconhecida: '{action}'. Disponiveis: {available}",
            available_actions=available,
        )

    def _read_file(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Caminho do arquivo nao especificado. Informe file_path.",
                available_actions=["list_directory", "get_capabilities"],
            )
        path = self._resolve(file_path)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}", file_path=str(path))
        try:
            content = path.read_text(encoding="utf-8")
            return TaskOutput.success(
                summary=f"Lido: {path}",
                rationale=f"Conteudo lido ({len(content)} chars)",
                path=str(path), size=len(content),
            )
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao ler {path}: {e}")

    def _write_file(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Caminho do arquivo nao especificado. Informe file_path.",
                available_actions=["list_directory"],
            )
        path = self._resolve(file_path)
        content = task.get("content", "")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            size = path.stat().st_size
            return TaskOutput.success(
                summary=f"Arquivo salvo: {path} ({size} bytes)",
                rationale=f"Escritos {size} bytes em {path.name}",
                path=str(path), bytes=size,
            )
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao escrever {path}: {e}")

    def _edit_file(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Caminho do arquivo nao especificado.",
                available_actions=["list_directory", "read_file"],
            )
        path = self._resolve(file_path)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
        old = task.get("old_string", "")
        new = task.get("new_string", "")
        if not old:
            return TaskOutput.needs_direction(rationale="'old_string' obrigatorio para editar.")
        try:
            content = path.read_text(encoding="utf-8")
            if old not in content:
                return TaskOutput.failure(rationale=f"'old_string' nao encontrado em {path}")
            count = content.count(old)
            new_content = content.replace(old, new, 1)
            path.write_text(new_content, encoding="utf-8")
            return TaskOutput.success(
                summary=f"Arquivo editado: {path} (1 substituicao de {count} ocorrencia(s))",
                rationale=f"Substituida 1 ocorrencia de {count} no total",
                path=str(path), replacements=count,
            )
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao editar {path}: {e}")

    def _list_directory(self, task: dict) -> TaskOutput:
        base_path = self._resolve(task.get("path", "."))
        pattern = task.get("pattern", "*")
        if not base_path.exists():
            return TaskOutput.failure(rationale=f"Diretorio nao encontrado: {base_path}")
        try:
            files = [str(p.relative_to(self.working_dir)) for p in sorted(base_path.glob(pattern))]
            return TaskOutput.success(
                summary=f"Listados {len(files)} arquivos em {base_path}",
                rationale=f"Padrao: {pattern}, encontrados: {len(files)}",
                path=str(base_path), files=files, count=len(files),
            )
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao listar {base_path}: {e}")

    def _run_script(self, task: dict) -> TaskOutput:
        script_path = self._resolve(task.get("script_path", ""))
        args = task.get("args", [])
        if not script_path.exists():
            return TaskOutput.failure(rationale=f"Script nao encontrado: {script_path}")
        cmd = [sys.executable, str(script_path)] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=self.working_dir)
            ok = result.returncode == 0
            (cls, msg) = (TaskOutput.success, "executado") if ok else (TaskOutput.failure, "falhou")
            return cls(
                summary=f"Script {script_path.name} {msg} (codigo {result.returncode})",
                rationale=result.stderr[:500] if not ok else f"stdout: {result.stdout[:200]}",
                returncode=result.returncode, stderr=result.stderr[-500:],
            )
        except subprocess.TimeoutExpired:
            return TaskOutput.failure(rationale=f"Script excedeu timeout de 120s: {script_path.name}")
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao executar script: {e}")

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
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao executar testes: {e}")

    def _run_git(self, task: dict) -> TaskOutput:
        args = task.get("args", [])
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=self.working_dir)
            ok = result.returncode == 0
            cls = TaskOutput.success if ok else TaskOutput.failure
            return cls(
                summary=f"git {'ok' if ok else 'falhou'} (codigo {result.returncode})",
                rationale=result.stderr[:500] if not ok else result.stdout[:500],
                returncode=result.returncode, stdout=result.stdout[:2000], stderr=result.stderr[:1000],
            )
        except subprocess.TimeoutExpired:
            return TaskOutput.failure(rationale="Git excedeu timeout de 60s")
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao executar git: {e}")

    def _rename_file(self, task: dict) -> TaskOutput:
        src = self._resolve(task.get("src", ""))
        dst = self._resolve(task.get("dst", ""))
        if not src or not dst:
            return TaskOutput.needs_direction(rationale="Parametros 'src' e 'dst' obrigatorios.")
        if not src.exists():
            return TaskOutput.failure(rationale=f"Origem nao encontrada: {src}")
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            return TaskOutput.success(summary=f"Renomeado: {src.name} -> {dst.name}", from_path=str(src), to_path=str(dst))
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao renomear: {e}")

    def _delete_file(self, task: dict) -> TaskOutput:
        fp = task.get("file_path") or task.get("path")
        if not fp:
            return TaskOutput.needs_direction(rationale="Parametro 'file_path' obrigatorio.")
        path = self._resolve(fp)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
        try:
            path.unlink()
            return TaskOutput.success(summary=f"Arquivo removido: {path}")
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao remover {path}: {e}")

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

    def _generate_code_with_llm(self, task: dict) -> TaskOutput:
        spec = task.get("spec") or task.get("prompt", "")
        if not spec:
            return TaskOutput.needs_direction(
                rationale="Especifique o que gerar no campo 'spec'.",
                available_actions=["read_file", "list_directory", "get_capabilities"],
            )
        language = task.get("language", "")
        output_path = task.get("output_path", "")

        context_prefix = self._build_context_prompt(task)
        lang_hint = f" na linguagem/stack {language}" if language else ""
        prompt = f"""{context_prefix}

Gere codigo para a seguinte especificacao{lang_hint}:

{spec}

Retorne APENAS o codigo gerado, sem explicacoes, dentro de um bloco ``` com a linguagem. 
Se houver multiplos arquivos, retorne cada um em seu proprio bloco ``` com o caminho como comentario no inicio."""

        system_prompt = "Voce e um engenheiro de software sênior. Gere codigo limpo, seguro e bem estruturado."
        llm_response = self._llm_think(prompt, system_prompt=system_prompt, max_tokens=16384)

        if llm_response:
            self._save_artifact(task, "llm_raw_response.md", llm_response)
            # Strip markdown code fences if present
            cleaned = llm_response.strip()
            if cleaned.startswith("```"):
                first_nl = cleaned.find("\n")
                if first_nl != -1:
                    cleaned = cleaned[first_nl + 1:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()
            result = {
                "status": "generated",
                "summary": f"Codigo gerado via LLM ({self._llm.__class__.__name__ if self._llm else 'N/A'})",
                "code": cleaned,
                "spec": spec,
            }
            if output_path:
                path = self._resolve(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(cleaned, encoding="utf-8")
                result["file_path"] = str(path)
                result["summary"] += f" -> {path}"
            return TaskOutput.success(**result)
        return TaskOutput.failure(
            rationale="LLM nao disponivel para geracao de codigo. Use write_file manualmente.",
            available_actions=["write_file", "read_file", "list_directory"],
        )

    def _implement_feature_with_llm(self, task: dict) -> TaskOutput:
        spec = task.get("spec") or task.get("prompt", "")
        if not spec:
            return TaskOutput.needs_direction(
                rationale="Especifique a feature no campo 'spec'.",
                available_actions=["read_file", "list_directory", "get_capabilities"],
            )
        output_path = task.get("output_path", "")

        context_prefix = self._build_context_prompt(task)
        prompt = f"""{context_prefix}

Analise a seguinte feature e planeje sua implementacao:

{spec}

Forneca:
1. Um plano de implementacao passo a passo
2. Os arquivos que precisam ser criados ou modificados
3. O codigo para cada arquivo

Retorne o plano seguido pelos blocos de codigo com ```."""
        system_prompt = "Voce e um arquiteto de software sênior. Planeje implementacoes claras e modulares."
        llm_response = self._llm_think(prompt, system_prompt=system_prompt, max_tokens=16384)

        if llm_response:
            self._save_artifact(task, "llm_raw_response.md", llm_response)
            result = {
                "status": "planned",
                "summary": f"Feature planejada via LLM ({self._llm.__class__.__name__ if self._llm else 'N/A'})",
                "plan": llm_response,
                "spec": spec,
            }
            if output_path:
                path = self._resolve(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(llm_response, encoding="utf-8")
                result["file_path"] = str(path)
            return TaskOutput.success(**result)
        return TaskOutput.failure(
            rationale="LLM nao disponivel para planejamento. Implemente manualmente.",
            available_actions=["write_file", "edit_file", "read_file"],
        )

    def _refactor_code_with_llm(self, task: dict) -> TaskOutput:
        file_path = task.get("file_path") or task.get("path")
        if not file_path:
            return TaskOutput.needs_direction(
                rationale="Informe file_path para refatorar.",
                available_actions=["read_file", "list_directory"],
            )
        path = self._resolve(file_path)
        if not path.exists():
            return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")

        instructions = task.get("instructions", "Melhore a qualidade, legibilidade e desempenho do codigo.")
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return TaskOutput.failure(rationale=f"Erro ao ler {path}: {e}")

        context_prefix = self._build_context_prompt(task)
        prompt = f"""{context_prefix}

Analise e refatore o seguinte codigo:

Instrucoes: {instructions}

```{path.suffix[1:] if path.suffix else ''}
{content}
```

Retorne APENAS o codigo refatorado completo dentro de um bloco ```."""
        system_prompt = "Voce e um engenheiro de software sênior especializado em refatoracao. Preserve a funcionalidade original."
        llm_response = self._llm_think(prompt, system_prompt=system_prompt, max_tokens=32000)

        if llm_response:
            self._save_artifact(task, "llm_raw_response.md", llm_response)
            self._save_artifact(task, "original_code.md", content)
            cleaned = llm_response.strip()
            if cleaned.startswith("```"):
                first_nl = cleaned.find("\n")
                if first_nl != -1:
                    cleaned = cleaned[first_nl + 1:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()
            # Validar saida: se for HTML, verificar tags essenciais
            if path.suffix in (".html", ".htm"):
                missing = []
                if "</html>" not in cleaned:
                    missing.append("</html>")
                if "<script>" in content and "</script>" not in cleaned:
                    missing.append("</script>")
                if missing:
                    return TaskOutput.failure(
                        rationale=f"LLM truncou o HTML — tags ausentes: {', '.join(missing)}. "
                                  f"Resposta: {len(cleaned)} chars (original: {len(content)}). "
                                  f"Use max_tokens maior ou divida em partes menores.",
                        available_actions=["edit_file", "write_file"],
                    )
            path.write_text(cleaned, encoding="utf-8")
            return TaskOutput.success(
                summary=f"Codigo refatorado via LLM e salvo em {path}",
                rationale=f"LLM: {self._llm.__class__.__name__ if self._llm else 'N/A'}",
                file_path=str(path), before_size=len(content), after_size=len(llm_response),
            )
        return TaskOutput.failure(
            rationale="LLM nao disponivel para refatoracao.",
            available_actions=["edit_file", "read_file"],
        )
