"""
Agent Orchestrator — Protocolo de Sinalização Padronizado
=========================================================
Formato de saída padronizado para comunicação entre agentes.
Inspirado em LangGraph + OpenTelemetry + CloudEvents.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


class AgentStatus(str, Enum):
    """Status possíveis de um agente."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"  # Aguardando input humano


class AgentRole(str, Enum):
    """Papel do agente na orquestração."""
    COORDINATOR = "coordinator"
    WORKER = "worker"
    REVIEWER = "reviewer"


class AgentEvent(BaseModel):
    """
    Evento padronizado emitido por qualquer agente.
    
    Formato inspirado em CloudEvents + OpenTelemetry spans.
    Cada agente emite eventos durante sua execução.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str  # Identificador único do agente
    agent_role: AgentRole
    status: AgentStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Contexto da tarefa
    task_id: str  # ID da tarefa sendo executada
    parent_task_id: Optional[str] = None  # Tarefa pai (delegação)
    project_id: str  # ID do projeto
    
    # Conteúdo
    message: str = ""  # Mensagem descritiva
    payload: dict[str, Any] = Field(default_factory=dict)  # Dados de saída
    error: Optional[str] = None  # Erro se falhou
    
    # Métricas
    metrics: dict[str, Any] = Field(default_factory=dict)
    # Exemplos: duration_ms, tokens_used, frames_processed, etc.
    
    # Rastreamento
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_span_id: Optional[str] = None


class TaskResult(BaseModel):
    """
    Resultado final de uma tarefa executada por um agente.
    
    Formato padronizado para consumo pelo Coordenador/Interface.
    """
    task_id: str
    agent_id: str
    project_id: str
    status: AgentStatus
    started_at: datetime
    completed_at: datetime
    
    # Saída
    output: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)  # Caminhos de arquivos gerados
    
    # Resumo para o usuário
    summary: str = ""  # Resumo legível por humanos
    details: dict[str, Any] = Field(default_factory=dict)  # Detalhes técnicos
    
    # Métricas agregadas
    total_duration_ms: float = 0
    metrics: dict[str, Any] = Field(default_factory=dict)
    
    # Labels para Event Log (correlação com GitHub Projects)
    title: str = ""  # Título da tarefa
    observation: str = ""  # Observação adicional
    description: str = ""  # Descrição detalhada


class TaskInput(BaseModel):
    """
    Entrada padronizada para tarefas dos agentes.
    
    Inclui campos para labels que aparecem no Event Log.
    """
    task_id: str
    title: str = ""  # Título da tarefa (aparece no Event Log)
    observation: str = ""  # Observação adicional
    description: str = ""  # Descrição detalhada
    
    # Para correlação com GitHub Projects
    github_issue: Optional[str] = None  # Ex: "PTA-123"
    github_pr: Optional[str] = None  # Ex: "PTA-456"
    
    # Dados da tarefa
    payload: dict[str, Any] = Field(default_factory=dict)


class ProjectConfig(BaseModel):
    """
    Configuração de um projeto no orchestrator.
    
    Permite reutilizar o mesmo orchestrator para diferentes projetos.
    """
    project_id: str
    name: str
    description: str = ""
    
    # Agentes disponíveis
    agents: list[dict[str, Any]] = Field(default_factory=list)
    
    # Configurações
    max_retries: int = 3
    timeout_seconds: int = 3600  # 1 hora
    enable_dashboard: bool = True
    dashboard_port: int = 8080
    
    # Webhooks/callbacks
    webhook_url: Optional[str] = None
    notification_enabled: bool = True
    
    # Contexto adicional
    context: dict[str, Any] = Field(default_factory=dict)


class OrchestratorState(BaseModel):
    """
    Estado do orchestrator.
    
    Persistido entre execuções via LangGraph checkpoints.
    """
    project_id: str
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Tarefas
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    completed_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)
    
    # Eventos
    events: list[AgentEvent] = Field(default_factory=list)
    
    # Estado atual
    current_phase: str = "initializing"
    progress: float = 0.0  # 0-100
    
    # Resultado final
    final_result: Optional[TaskResult] = None
