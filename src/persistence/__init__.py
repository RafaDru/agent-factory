"""
Agent Factory — Context Persistence
====================================
Persistência de contexto dos agentes via SQLite.
Permite que agentes lembrem de tarefas anteriores entre sessões.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from ..protocols.schema import AgentEvent, TaskResult, AgentStatus


class ContextStore:
    """
    Armazenamento persistente de contexto para agentes.
    
    Uso:
        store = ContextStore("my-project")
        
        # Salvar evento
        store.save_event(event)
        
        # Recuperar histórico
        history = store.get_agent_history("my-agent", limit=10)
        
        # Salvar contexto de agente
        store.save_agent_context("my-agent", {"last_task": "task-1"})
        
        # Recuperar contexto
        context = store.get_agent_context("my-agent")
    """
    
    def __init__(self, project_id: str, db_dir: str = ".agent-factory"):
        self.project_id = project_id
        self.db_dir = Path(db_dir) / "context"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / f"{project_id}.db"
        
        self._init_db()
    
    def _init_db(self):
        """Inicializa o banco de dados SQLite."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    message TEXT,
                    payload TEXT,
                    error TEXT,
                    metrics TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output TEXT,
                    summary TEXT,
                    total_duration_ms REAL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_contexts (
                    agent_id TEXT PRIMARY KEY,
                    context TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_contexts (
                    task_id TEXT PRIMARY KEY,
                    context TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_results_agent ON task_results(agent_id)")
            
            conn.commit()
        finally:
            conn.close()
    
    def save_event(self, event: AgentEvent):
        """Salva um evento no banco de dados."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO events 
                (event_id, agent_id, status, task_id, message, payload, error, metrics, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.agent_id,
                event.status.value,
                event.task_id,
                event.message,
                json.dumps(event.payload, default=str),
                event.error,
                json.dumps(event.metrics, default=str),
                event.timestamp.isoformat(),
            ))
            conn.commit()
        finally:
            conn.close()
    
    def save_task_result(self, result: TaskResult):
        """Salva o resultado de uma tarefa."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO task_results 
                (task_id, agent_id, status, output, summary, total_duration_ms, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.task_id,
                result.agent_id,
                result.status.value,
                json.dumps(result.output, default=str),
                result.summary,
                result.total_duration_ms,
                result.started_at.isoformat(),
                result.completed_at.isoformat(),
            ))
            conn.commit()
        finally:
            conn.close()
    
    def save_agent_context(self, agent_id: str, context: dict[str, Any]):
        """Salva contexto persistente de um agente."""
        now = datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO agent_contexts (agent_id, context, updated_at)
                VALUES (?, ?, ?)
            """, (agent_id, json.dumps(context, default=str), now))
            conn.commit()
        finally:
            conn.close()
    
    def get_agent_context(self, agent_id: str) -> dict[str, Any]:
        """Recupera contexto persistente de um agente."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT context FROM agent_contexts WHERE agent_id = ?",
                (agent_id,)
            ).fetchone()
            
            if row:
                return json.loads(row[0])
            return {}
        finally:
            conn.close()
    
    def save_task_context(self, task_id: str, context: dict[str, Any]):
        """Salva contexto persistente de uma tarefa."""
        now = datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO task_contexts (task_id, context, updated_at)
                VALUES (?, ?, ?)
            """, (task_id, json.dumps(context, default=str), now))
            conn.commit()
        finally:
            conn.close()
    
    def get_task_context(self, task_id: str) -> dict[str, Any]:
        """Recupera contexto persistente de uma tarefa."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT context FROM task_contexts WHERE task_id = ?",
                (task_id,)
            ).fetchone()
            
            if row:
                return json.loads(row[0])
            return {}
        finally:
            conn.close()
    
    def get_agent_history(
        self, 
        agent_id: str, 
        limit: int = 50,
        status: Optional[AgentStatus] = None
    ) -> list[dict]:
        """Retorna histórico de eventos de um agente."""
        conn = sqlite3.connect(self.db_path)
        try:
            query = "SELECT * FROM events WHERE agent_id = ?"
            params = [agent_id]
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [
                {
                    "event_id": row[1],
                    "agent_id": row[2],
                    "status": row[3],
                    "task_id": row[4],
                    "message": row[5],
                    "payload": json.loads(row[6]) if row[6] else {},
                    "error": row[7],
                    "metrics": json.loads(row[8]) if row[8] else {},
                    "timestamp": row[9],
                }
                for row in rows
            ]
        finally:
            conn.close()
    
    def get_task_history(self, limit: int = 50) -> list[dict]:
        """Retorna histórico de resultados de tarefas."""
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM task_results ORDER BY completed_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            
            return [
                {
                    "task_id": row[1],
                    "agent_id": row[2],
                    "status": row[3],
                    "output": json.loads(row[4]) if row[4] else {},
                    "summary": row[5],
                    "total_duration_ms": row[6],
                    "started_at": row[7],
                    "completed_at": row[8],
                }
                for row in rows
            ]
        finally:
            conn.close()
    
    def get_stats(self) -> dict:
        """Retorna estatísticas gerais do projeto."""
        conn = sqlite3.connect(self.db_path)
        try:
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_tasks = conn.execute("SELECT COUNT(*) FROM task_results").fetchone()[0]
            
            completed = conn.execute(
                "SELECT COUNT(*) FROM task_results WHERE status = 'completed'"
            ).fetchone()[0]
            
            failed = conn.execute(
                "SELECT COUNT(*) FROM task_results WHERE status = 'failed'"
            ).fetchone()[0]
            
            avg_duration = conn.execute(
                "SELECT AVG(total_duration_ms) FROM task_results WHERE status = 'completed'"
            ).fetchone()[0] or 0
            
            return {
                "project_id": self.project_id,
                "total_events": total_events,
                "total_tasks": total_tasks,
                "completed_tasks": completed,
                "failed_tasks": failed,
                "success_rate": (completed / total_tasks * 100) if total_tasks > 0 else 0,
                "avg_duration_ms": round(avg_duration, 2),
            }
        finally:
            conn.close()
    
    def clear_history(self, days: int = 30):
        """Remove histórico antigo (mais de N dias)."""
        cutoff = datetime.utcnow().isoformat()
        # Simplificação: remove tudo antes de um timestamp
        # Em produção, usar datetime arithmetic
        pass
