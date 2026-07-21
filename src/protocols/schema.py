"""
Agent Orchestrator — Protocolo de Sinalização Padronizado
=========================================================
Formato de saída padronizado para comunicação entre agentes.
Inspirado em LangGraph + OpenTelemetry + CloudEvents.
"""

from datetime import datetime, timezone
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


class OutputStatus(str, Enum):
    """
    Status de saida de um agente apos execucao.
    Define o resultado semantico — nao o ciclo de vida.
    """
    SUCCESS = "success"                          # Executou completamente
    PARTIAL_SUCCESS = "partial_success"          # Executou com ressalvas
    FAILURE = "failure"                          # Nao conseguiu executar
    NEEDS_DIRECTION = "needs_direction"          # Objetivo ambiguo, precisa de esclarecimento
    NEEDS_AUTHORIZATION = "needs_authorization"  # Requer autorizacao para prosseguir
    REJECTED = "rejected"                        # Recusou por politica/seguranca
    DELEGATED = "delegated"                      # Repassou para outro agente
    REQUESTED_ACTION = "requested_action"        # Requer acao do agente pai


class AgentRole(str, Enum):
    """Papel do agente na orquestração."""
    COORDINATOR = "coordinator"
    WORKER = "worker"
    REVIEWER = "reviewer"
    DESIGNER = "designer"
    ARCHITECT = "architect"


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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Contexto da tarefa
    task_id: str  # ID da tarefa sendo executada
    parent_task_id: Optional[str] = None  # Tarefa pai (delegação)
    project_id: str  # ID do projeto
    mission_id: Optional[str] = None  # ID da missão (agrupamento de tarefas)
    
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


class TaskOutput(BaseModel):
    """
    Saída padronizada de uma tarefa executada por um agente.
    
    Agrupa resultado + metadados + raciocínio em um único struct.
    """
    status: OutputStatus
    rationale: str = ""
    summary: str = ""
    details: Optional[dict[str, Any]] = None
    available_actions: Optional[list[str]] = None
    
    delegated_to: Optional[str] = None
    delegated_result: Optional["TaskOutput"] = None
    
    requested_action: Optional[str] = None
    requested_params: Optional[dict[str, Any]] = None
    
    duration_ms: float = 0
    metrics: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_execute_output(cls, output: dict) -> "TaskOutput":
        """
        Converte dict retornado por execute() para TaskOutput.
        Mantem compatibilidade com workers que ainda retornam dicts simples.
        """
        raw_status = output.get("status", "success")
        if raw_status == "ok":
            status = OutputStatus.SUCCESS
        elif raw_status == "error":
            status = OutputStatus.FAILURE
        elif raw_status == "partial":
            status = OutputStatus.PARTIAL_SUCCESS
        elif raw_status == "warning":
            status = OutputStatus.SUCCESS
        elif isinstance(raw_status, OutputStatus):
            status = raw_status
        else:
            status = OutputStatus(raw_status)

        error = output.get("error") or output.get("message", "")
        rationale = output.get("rationale") or error or ""
        summary = output.get("summary") or output.get("message") or output.get("status", "")
        available = output.get("available_actions")

        details = {k: v for k, v in output.items()
                   if k not in ("status", "rationale", "summary",
                                "available_actions", "error")}
        if not details:
            details = None

        return cls(
            status=status,
            rationale=rationale,
            summary=summary,
            details=details or output,
            available_actions=available,
        )

    @classmethod
    def success(cls, summary: str = "", rationale: str = "", **details) -> "TaskOutput":
        return cls(status=OutputStatus.SUCCESS, summary=summary, rationale=rationale, details=details or None)

    @classmethod
    def failure(cls, rationale: str, summary: str = "", available_actions: Optional[list[str]] = None, **details) -> "TaskOutput":
        return cls(status=OutputStatus.FAILURE, rationale=rationale, summary=summary or rationale,
                   available_actions=available_actions, details=details or None)

    @classmethod
    def partial(cls, summary: str, rationale: str = "", **details) -> "TaskOutput":
        return cls(status=OutputStatus.PARTIAL_SUCCESS, summary=summary, rationale=rationale, details=details or None)

    @classmethod
    def needs_direction(cls, rationale: str, available_actions: Optional[list[str]] = None) -> "TaskOutput":
        return cls(status=OutputStatus.NEEDS_DIRECTION, rationale=rationale, summary=rationale,
                   available_actions=available_actions)

    @classmethod
    def delegated(cls, to: str, result: "TaskOutput", summary: str = "") -> "TaskOutput":
        return cls(status=OutputStatus.DELEGATED, delegated_to=to, delegated_result=result,
                   summary=summary or f"Delegado para {to}")


# Resolver forward reference
TaskOutput.model_rebuild()


class Decision(str, Enum):
    """
    Decisao do motor de orquestracao apos avaliar um resultado de agente.
    """
    ACCEPT = "accept"                          # Resultado aceitavel, prosseguir
    RETRY = "retry"                            # Tentar novamente com correcao
    RETRY_ALTERNATIVE = "retry_alternative"    # Tentar acao diferente
    REPLAN = "replan"                          # Gerar novo plano
    ESCALATE = "escalate"                      # Escalar para humano/pai
    SKIP = "skip"                              # Ignorar e continuar
    ABORT = "abort"                            # Abortar toda execucao
