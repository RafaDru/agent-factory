"""
Agent Orchestrator — Event Emitter
===================================
Emite eventos para o dashboard e notificações.
Suporta SSE (Server-Sent Events) e arquivos JSON.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable
from .schema import AgentEvent, AgentStatus, TaskResult


def _maybe_publish_to_rabbitmq(event: AgentEvent):
    """Publica evento no RabbitMQ se o modulo estiver disponivel."""
    try:
        import pika
        from src.eventbus.amqp import AMQPConnection
        conn = AMQPConnection()
        conn.connect()
        ch = conn.channel
        if ch and ch.is_open:
            ch.basic_publish(
                exchange="afp",
                routing_key=f"event.broadcast.{event.project_id}",
                body=event.model_dump_json().encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2, content_type="application/json"
                ),
            )
        conn.close()
    except Exception:
        pass  # RabbitMQ indisponivel, evento apenas local


class EventNotifier:
    """
    Notificador de eventos para múltiplos canais.
    
    Canais suportados:
    - Arquivo JSON (persistência)
    - SSE (dashboard real-time)
    - Callback (para integração)
    """
    
    _sse_clients: set = set()
    _last_event_id: int = 0
    
    def __init__(self, project_id: str, output_dir: str = ".agent-events"):
        self.project_id = project_id
        self.output_dir = Path(output_dir) / project_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._callbacks: list[Callable[[AgentEvent], None]] = []
        self._events_file = self.output_dir / "events.jsonl"
        self._status_file = self.output_dir / "status.json"
        self._result_file = self.output_dir / "result.json"
        
        # Inicializar status
        self._update_status("initializing", 0)
    
    @classmethod
    def register_sse_client(cls, client):
        """Registra um cliente SSE para receber eventos."""
        cls._sse_clients.add(client)
    
    @classmethod
    def unregister_sse_client(cls, client):
        """Remove um cliente SSE."""
        cls._sse_clients.discard(client)

    def _notify_sse_clients(self, event: AgentEvent):
        """Envia evento para todos os clientes SSE registrados."""
        EventNotifier._last_event_id += 1
        event_id = EventNotifier._last_event_id
        event_json = event.model_dump_json()

        message = f"event: agent_event\nid: {event_id}\ndata: {event_json}\n\n"
        
        for client in list(EventNotifier._sse_clients):
            try:
                client.wfile.write(message.encode("utf-8"))
                client.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                EventNotifier.unregister_sse_client(client)
    
    def on_event(self, callback: Callable[[AgentEvent], None]):
        """Registra callback para eventos."""
        self._callbacks.append(callback)
    
    def emit(self, event: AgentEvent, _from_rabbitmq: bool = False):
        """Emite evento para todos os canais."""
        # 1. Salvar em arquivo JSONL
        with open(self._events_file, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
        
        # 2. Atualizar status
        self._update_status_from_event(event)
        
        # 3. Chamar callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Callback error: {e}")
        
        # 4. Notificar clientes SSE
        self._notify_sse_clients(event)

        # 5. Publicar no RabbitMQ (se disponivel e nao for evento reentrante)
        if not _from_rabbitmq:
            _maybe_publish_to_rabbitmq(event)
    
    def emit_task_result(self, result: TaskResult):
        """Emite resultado final de tarefa."""
        # Salvar resultado
        with open(self._result_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)
        
        # Criar evento de conclusão
        event = AgentEvent(
            agent_id=result.agent_id,
            agent_role="worker",
            status=result.status,
            task_id=result.task_id,
            project_id=self.project_id,
            message=result.summary,
            payload=result.output,
            metrics={
                "duration_ms": result.total_duration_ms,
                **result.metrics
            }
        )
        self.emit(event)
    
    def _update_status_from_event(self, event: AgentEvent):
        """Atualiza arquivo de status baseado no evento."""
        # Calcular progresso
        events = self._read_events()
        total = len([e for e in events if e.status != AgentStatus.PENDING])
        completed = len([e for e in events if e.status == AgentStatus.COMPLETED])
        failed = len([e for e in events if e.status == AgentStatus.FAILED])
        
        if total > 0:
            progress = ((completed + failed) / total) * 100
        else:
            progress = 0
        
        # Determinar fase
        if event.status == AgentStatus.RUNNING:
            phase = f"running:{event.agent_id}"
        elif event.status == AgentStatus.COMPLETED:
            phase = f"completed:{event.agent_id}"
        elif event.status == AgentStatus.FAILED:
            phase = f"failed:{event.agent_id}"
        else:
            phase = event.status.value
        
        self._update_status(phase, progress)
    
    def _update_status(self, phase: str, progress: float):
        """Atualiza arquivo de status."""
        status = {
            "project_id": self.project_id,
            "phase": phase,
            "progress": progress,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._status_file, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
    
    def _read_events(self) -> list[AgentEvent]:
        """Lê eventos do arquivo."""
        if not self._events_file.exists():
            return []
        
        events = []
        with open(self._events_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(AgentEvent.model_validate_json(line))
        return events
    
    def get_status(self) -> dict:
        """Retorna status atual."""
        if self._status_file.exists():
            with open(self._status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"phase": "unknown", "progress": 0}
    
    def get_events(self) -> list[AgentEvent]:
        """Retorna todos os eventos."""
        return self._read_events()
    
    def get_result(self) -> Optional[TaskResult]:
        """Retorna resultado final se disponível."""
        if self._result_file.exists():
            with open(self._result_file, "r", encoding="utf-8") as f:
                return TaskResult.model_validate(json.load(f))
        return None
    
    def is_complete(self) -> bool:
        """Verifica se a execução está completa."""
        status = self.get_status()
        return status.get("phase", "").startswith("completed") or \
               status.get("phase", "").startswith("failed")
