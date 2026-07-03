"""
Agent Orchestrator — Base Agent
====================
Classes abstratas para agentes componentizados.
Cada agente é um módulo independente que pode ser reutilizado.

Context Tracking Features:
- Mede tamanho do arquivo de contexto (KB)
- Estima tokens (1 token ≈ 4 chars para português)
- Auto-compressão quando contexto > 80%
- Métricas incluídas automaticamente nos eventos
"""

import os
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from ..protocols.schema import (
    AgentEvent, AgentStatus, AgentRole, TaskResult
)
from ..protocols.events import EventNotifier


class ContextManager:
    """
    Gerencia contexto de agentes com suporte a tokens e auto-compressão.
    
    Features:
    - Mede tamanho em KB e tokens
    - Estima tokens (1 token ≈ 4 chars)
    - Auto-comprime quando > 80%
    - Histórico de crescimento
    """
    
    CHARS_PER_TOKEN = 4
    DEFAULT_TOKEN_LIMIT = 32000

    COMPRESSION_PROMPT = """Resuma cada seção do contexto abaixo preservando:
1. Decisões e acordos contratuais
2. Dados numéricos e métricas
3. Restrições e regras de negócio
4. Dependências entre tarefas

Seja conciso. Remova repetições."""
    
    def __init__(
        self,
        context_file: Optional[Path] = None,
        limit_kb: float = 15.0,
        token_limit: int = DEFAULT_TOKEN_LIMIT,
        warn_at_percentage: float = 80.0,
        auto_compress: bool = True,
        llm_provider: Optional[Any] = None,
    ):
        self.context_file = context_file
        self.limit_kb = limit_kb
        self.token_limit = token_limit
        self.warn_at_percentage = warn_at_percentage
        self.auto_compress = auto_compress
        self.llm_provider = llm_provider
        self._usage_history: list[dict] = []
        self._last_compressed_at: Optional[str] = None
        self._compressing: bool = False
    
    def count_tokens(self, text: str) -> int:
        """Estima número de tokens no texto."""
        if not text:
            return 0
        
        char_count = len(text)
        words = re.findall(r'\S+', text)
        word_count = len(words)
        
        tokens_by_chars = char_count // self.CHARS_PER_TOKEN
        tokens_by_words = int(word_count * 1.3)
        
        return max(tokens_by_chars, tokens_by_words)
    
    def get_file_size_kb(self) -> float:
        """Retorna tamanho do arquivo em KB."""
        if not self.context_file or not self.context_file.exists():
            return 0.0
        
        size_bytes = self.context_file.stat().st_size
        return round(size_bytes / 1024, 2)
    
    def get_usage(self) -> dict[str, Any]:
        """Retorna métricas completas de uso de contexto."""
        if not self.context_file or not self.context_file.exists():
            return {
                "used_kb": 0.0,
                "limit_kb": self.limit_kb,
                "tokens": 0,
                "token_limit": self.token_limit,
                "percentage": 0.0,
                "token_percentage": 0.0,
                "status": "no_context",
                "path": str(self.context_file) if self.context_file else None,
                "needs_compression": False,
                "last_compressed_at": self._last_compressed_at,
                "compressing": False,
            }
        
        try:
            content = self.context_file.read_text(encoding="utf-8")
        except Exception:
            content = ""
        
        size_kb = self.get_file_size_kb()
        tokens = self.count_tokens(content)
        
        kb_percentage = round((size_kb / self.limit_kb) * 100, 1)
        token_percentage = round((tokens / self.token_limit) * 100, 1)
        percentage = token_percentage
        
        if percentage < self.warn_at_percentage:
            status = "ok"
        elif percentage < 100:
            status = "warning"
        else:
            status = "exhausted"
        
        needs_compression = self.auto_compress and percentage >= self.warn_at_percentage
        
        usage = {
            "used_kb": size_kb,
            "limit_kb": self.limit_kb,
            "tokens": tokens,
            "token_limit": self.token_limit,
            "percentage": percentage,
            "token_percentage": token_percentage,
            "kb_percentage": kb_percentage,
            "status": status,
            "path": str(self.context_file),
            "needs_compression": needs_compression,
            "last_compressed_at": self._last_compressed_at,
            "compressing": self._compressing,
        }
        
        self._usage_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "usage": usage.copy(),
        })
        
        if len(self._usage_history) > 100:
            self._usage_history = self._usage_history[-100:]
        
        return usage
    
    def compress(self, content: str, target_percentage: float = 60.0, llm_provider: Optional[Any] = None) -> str:
        """Comprime contexto — estrutural ou via LLM se provider disponível."""
        if not content:
            return content

        provider = llm_provider or self.llm_provider
        if provider:
            return self._compress_with_llm(content, target_percentage, provider)

        return self._compress_structural(content, target_percentage)

    def _compress_structural(self, content: str, target_percentage: float = 60.0) -> str:
        """Compressão estrutural: mantém topo/fim de cada seção, corta meio."""
        lines = content.split('\n')
        compressed_lines = []
        in_code_block = False
        section_lines = []
        current_section = None

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                compressed_lines.append(line)
                continue
            if in_code_block:
                compressed_lines.append(line)
                continue
            if stripped.startswith('#'):
                if current_section and len(section_lines) > 20:
                    compressed_lines.append(f"## {current_section} (resumido)")
                    compressed_lines.extend(section_lines[:10])
                    compressed_lines.append("...")
                    compressed_lines.extend(section_lines[-5:])
                else:
                    compressed_lines.extend(section_lines)
                current_section = stripped
                section_lines = []
                continue
            section_lines.append(line)

        if current_section and len(section_lines) > 20:
            compressed_lines.append(f"## {current_section} (resumido)")
            compressed_lines.extend(section_lines[:10])
            compressed_lines.append("...")
            compressed_lines.extend(section_lines[-5:])
        else:
            compressed_lines.extend(section_lines)

        result = []
        prev_empty = False
        for line in compressed_lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            result.append(line)
            prev_empty = is_empty

        compressed = '\n'.join(result)
        current_tokens = self.count_tokens(compressed)
        target_tokens = int(self.token_limit * (target_percentage / 100))

        if current_tokens > target_tokens:
            lines = compressed.split('\n')
            keep_start = len(lines) // 3
            keep_end = len(lines) // 6
            compressed = '\n'.join(lines[:keep_start]) + \
                        f"\n\n<!-- Contexto comprimido: {current_tokens} tokens -> {target_tokens} tokens -->\n\n" + \
                        '\n'.join(lines[-keep_end:])

        return compressed

    def _compress_with_llm(self, content: str, target_percentage: float, provider: Any) -> str:
        """Compressão via LLM: cada seção é resumida preservando acordos."""
        import json
        lines = content.split('\n')
        sections: list[dict] = []
        current_heading = "geral"
        current_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') and not stripped.startswith('## '):
                if current_lines:
                    sections.append({"heading": current_heading, "body": '\n'.join(current_lines).strip()})
                current_heading = stripped.lstrip('#').strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({"heading": current_heading, "body": '\n'.join(current_lines).strip()})

        current_tokens = self.count_tokens(content)
        target_tokens = int(self.token_limit * (target_percentage / 100))

        # Seção por seção: só resume se estourarem o alvo
        compressed_sections = []
        estimated = 0
        for sec in sections:
            sec_tokens = self.count_tokens(sec["body"])
            if estimated + sec_tokens <= target_tokens:
                compressed_sections.append(f"# {sec['heading']}\n{sec['body']}")
                estimated += sec_tokens
            else:
                prompt = f"{self.COMPRESSION_PROMPT}\n\n## {sec['heading']}\n\n{sec['body'][:8000]}"
                try:
                    resp = provider.chat(
                        messages=[
                            {"role": "system", "content": "Você é um compressor de contexto. Seja direto."},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=max(200, target_tokens // max(len(sections), 1)),
                    )
                    compressed_sections.append(f"# {sec['heading']} (comprimido)\n{resp.content.strip()}")
                    estimated += self.count_tokens(resp.content)
                except Exception:
                    compressed_sections.append(f"# {sec['heading']}\n{sec['body'][:1000]}...")
                    estimated += 1000

        result = '\n\n'.join(compressed_sections)
        result += f"\n\n<!-- Contexto comprimido via LLM: {current_tokens} tokens -> {self.count_tokens(result)} tokens -->"
        return result

    def auto_compress_if_needed(self, llm_provider: Optional[Any] = None) -> bool:
        """Comprime automaticamente se necessário."""
        if not self.auto_compress or not self.context_file:
            return False
        
        usage = self.get_usage()
        
        if not usage["needs_compression"]:
            return False
        
        try:
            self._compressing = True
            content = self.context_file.read_text(encoding="utf-8")
            compressed = self.compress(content, llm_provider=llm_provider or self.llm_provider)
            
            backup_path = self.context_file.with_suffix('.bak.md')
            backup_path.write_text(content, encoding="utf-8")
            
            self.context_file.write_text(compressed, encoding="utf-8")
            self._last_compressed_at = datetime.utcnow().isoformat()
            return True
        except Exception:
            return False
        finally:
            self._compressing = False
    
    def get_growth_history(self) -> list[dict]:
        """Retorna histórico de crescimento do contexto."""
        return self._usage_history
    
    def get_growth_trend(self) -> dict:
        """Analisa tendência de crescimento."""
        if len(self._usage_history) < 2:
            return {
                "trend": "unknown",
                "tokens_per_hour": 0,
                "hours_until_full": None,
            }
        
        first = self._usage_history[0]
        last = self._usage_history[-1]
        
        first_time = datetime.fromisoformat(first["timestamp"])
        last_time = datetime.fromisoformat(last["timestamp"])
        
        hours_diff = (last_time - first_time).total_seconds() / 3600
        if hours_diff <= 0:
            hours_diff = 0.001
        
        tokens_diff = last["usage"]["tokens"] - first["usage"]["tokens"]
        tokens_per_hour = tokens_diff / hours_diff
        
        remaining_tokens = self.token_limit - last["usage"]["tokens"]
        if tokens_per_hour > 0:
            hours_until_full = remaining_tokens / tokens_per_hour
        else:
            hours_until_full = None
        
        if tokens_per_hour > 100:
            trend = "growing"
        elif tokens_per_hour < -100:
            trend = "shrinking"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "tokens_per_hour": round(tokens_per_hour, 1),
            "hours_until_full": round(hours_until_full, 1) if hours_until_full else None,
            "current_tokens": last["usage"]["tokens"],
            "limit_tokens": self.token_limit,
        }


class AgentBase(ABC):
    """
    Classe base abstrata para todos os agentes.
    
    Cada agente deve:
    1. Implementar execute() com a lógica principal
    2. Declarar seus inputs/outputs via schema
    3. Emite eventos via notifier durante a execução
    
    Context Tracking:
    - Cada agente pode ter um arquivo de contexto associado
    - get_context_usage() mede o tamanho atual vs limite
    - Contagem de tokens estimada (1 token ≈ 4 chars)
    - Auto-compressão quando contexto > 80%
    - Métricas incluídas automaticamente nos eventos
    """
    
    def __init__(
        self,
        agent_id: str,
        project_id: str,
        notifier: EventNotifier,
        role: AgentRole = AgentRole.WORKER,
        context_limit_kb: float = 15.0,
        context_file: Optional[str] = None,
        token_limit: int = 32000,
        auto_compress: bool = True,
        llm_provider: Optional[Any] = None,
    ):
        self.agent_id = agent_id
        self.project_id = project_id
        self.notifier = notifier
        self.role = role
        self.llm_provider = llm_provider
        self._start_time: Optional[datetime] = None
        self._current_task: Optional[dict] = None
        
        self._context_manager = ContextManager(
            context_file=Path(context_file) if context_file else None,
            limit_kb=context_limit_kb,
            token_limit=token_limit,
            warn_at_percentage=80.0,
            auto_compress=auto_compress,
            llm_provider=llm_provider,
        )
    
    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Executa a tarefa principal do agente."""
        pass
    
    @abstractmethod
    def validate_input(self, task: dict[str, Any]) -> bool:
        """Valida se os inputs da tarefa são válidos."""
        pass
    
    def run(self, task: dict[str, Any]) -> TaskResult:
        """Executa o agente completo com tracking de eventos."""
        task_id = task.get("task_id", "unknown")
        self._start_time = datetime.utcnow()
        self._current_task = task
        
        title = task.get("title", "Sem titulo")
        observation = task.get("observation", "")
        description = task.get("description", "Execucao de tarefa")
        
        label = f"{title}"
        if observation:
            label += f" - {observation}"
        self._emit(AgentStatus.RUNNING, f"Iniciando: {label}", task)
        
        try:
            if not self.validate_input(task):
                raise ValueError(f"Input invalido para tarefa {task_id}")
            
            self._emit(AgentStatus.RUNNING, f"Executando: {label}", task)
            
            self._context_manager.auto_compress_if_needed(llm_provider=self.llm_provider)
            
            output = self.execute(task)
            
            self._emit(AgentStatus.COMPLETED, f"Concluido: {label}", task, payload=output)
            
            return self._build_result(task, AgentStatus.COMPLETED, output)
            
        except Exception as e:
            self._emit(AgentStatus.FAILED, f"Erro: {label} - {str(e)}", task, error=str(e))
            return self._build_result(task, AgentStatus.FAILED, error=str(e))
    
    def _emit(
        self,
        status: AgentStatus,
        message: str,
        task: dict[str, Any],
        payload: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        """Emite evento para o notifier."""
        event = AgentEvent(
            agent_id=self.agent_id,
            agent_role=self.role,
            status=status,
            task_id=task.get("task_id", "unknown"),
            parent_task_id=task.get("parent_task_id"),
            project_id=self.project_id,
            message=message,
            payload=payload or {},
            error=error,
            metrics=self._get_metrics(),
        )
        self.notifier.emit(event)
    
    def _get_metrics(self) -> dict[str, Any]:
        """Retorna métricas atuais do agente, incluindo contexto."""
        metrics = {}
        if self._start_time:
            duration = (datetime.utcnow() - self._start_time).total_seconds()
            metrics["duration_seconds"] = duration
        
        metrics["context"] = self.get_context_usage()
        
        return metrics
    
    def get_context_usage(self) -> dict[str, Any]:
        """Mede uso atual de contexto do agente."""
        return self._context_manager.get_usage()
    
    def count_tokens(self, text: str) -> int:
        """Estima número de tokens no texto."""
        return self._context_manager.count_tokens(text)
    
    def get_growth_trend(self) -> dict:
        """Analisa tendência de crescimento do contexto."""
        return self._context_manager.get_growth_trend()
    
    def set_context_file(self, path: str):
        """Define o arquivo de contexto do agente."""
        self._context_manager.context_file = Path(path)
    
    def set_context_limit(self, limit_kb: float):
        """Define o limite de contexto em KB."""
        self._context_manager.limit_kb = limit_kb
    
    def persist_context(self, content: str) -> bool:
        """Persiste conteúdo no arquivo de contexto."""
        if not self._context_manager.context_file:
            return False
        
        try:
            self._context_manager.context_file.parent.mkdir(parents=True, exist_ok=True)
            self._context_manager.context_file.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False
    
    def read_context(self) -> str:
        """Lê o conteúdo do arquivo de contexto."""
        if not self._context_manager.context_file or not self._context_manager.context_file.exists():
            return ""
        
        try:
            return self._context_manager.context_file.read_text(encoding="utf-8")
        except Exception:
            return ""
    
    def should_persist(self) -> bool:
        """Verifica se o contexto deve ser persistido."""
        usage = self.get_context_usage()
        return usage["needs_compression"]
    
    def compress_context(self, target_percentage: float = 60.0) -> bool:
        """Comprime contexto manualmente."""
        return self._context_manager.auto_compress_if_needed(llm_provider=self.llm_provider)
    
    def _build_result(
        self,
        task: dict[str, Any],
        status: AgentStatus,
        output: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> TaskResult:
        """Constrói o resultado final da tarefa."""
        end_time = datetime.utcnow()
        duration = 0
        if self._start_time:
            duration = (end_time - self._start_time).total_seconds() * 1000
        
        return TaskResult(
            task_id=task.get("task_id", "unknown"),
            agent_id=self.agent_id,
            project_id=self.project_id,
            status=status,
            started_at=self._start_time or end_time,
            completed_at=end_time,
            output=output or {},
            summary=f"Tarefa {status.value}: {task.get('description', 'sem descricao')}",
            total_duration_ms=duration,
        )


class CoordinatorAgent(AgentBase):
    """
    Agente coordenador que delega tarefas a workers.
    """
    
    def __init__(self, agent_id: str, project_id: str, notifier: EventNotifier):
        super().__init__(agent_id, project_id, notifier, AgentRole.COORDINATOR)
        self._workers: dict[str, AgentBase] = {}
    
    def register_worker(self, worker: AgentBase):
        """Registra um worker subordinado."""
        self._workers[worker.agent_id] = worker
    
    def delegate(self, task: dict[str, Any], worker_id: str) -> TaskResult:
        """Delega tarefa a um worker específico."""
        if worker_id not in self._workers:
            raise ValueError(f"Worker {worker_id} não registrado")
        
        self._emit(
            AgentStatus.RUNNING,
            f"Delegando tarefa para {worker_id}",
            task
        )
        
        worker = self._workers[worker_id]
        return worker.run(task)
    
    def delegate_all(self, task: dict[str, Any]) -> dict[str, TaskResult]:
        """Delega tarefa a todos os workers registrados."""
        results = {}
        for worker_id, worker in self._workers.items():
            results[worker_id] = self.delegate(task, worker_id)
        return results
