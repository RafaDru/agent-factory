"""
Agent Orchestrator — LangGraph Graph
=====================================
Graph principal de orquestração usando LangGraph.
Suporta múltiplos projetos via configuração.
"""

import json
from datetime import datetime
from typing import Any, Optional, Literal
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..protocols.schema import (
    OrchestratorState, AgentEvent, AgentStatus, ProjectConfig
)
from ..protocols.events import EventNotifier
from ..agents.base import AgentBase, CoordinatorAgent
from ..notifications.windows import send_completion_notification, send_error_notification


class OrchestratorGraph:
    """
    Graph de orquestração principal.
    
    Uso:
        config = ProjectConfig(project_id="pta", name="Personal Trainer Agent")
        orchestrator = OrchestratorGraph(config)
        orchestrator.add_agent(my_agent)
        result = orchestrator.run({"task": "..."})
    """
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.notifier = EventNotifier(config.project_id)
        self._agents: dict[str, AgentBase] = {}
        self._coordinator: Optional[CoordinatorAgent] = None
        self._graph = None
        self._checkpointer = MemorySaver()
        
        self._build_graph()
    
    def add_agent(self, agent: AgentBase):
        """Adiciona um agente ao orchestrator."""
        self._agents[agent.agent_id] = agent
        
        # Se for coordenador, registrar
        if agent.role.value == "coordinator":
            self._coordinator = agent
    
    def _build_graph(self):
        """Constrói o LangGraph state graph."""
        # Definir states
        workflow = StateGraph(OrchestratorState)
        
        # Adicionar nós
        workflow.add_node("initialize", self._node_initialize)
        workflow.add_node("plan", self._node_plan)
        workflow.add_node("execute", self._node_execute)
        workflow.add_node("review", self._node_review)
        workflow.add_node("finalize", self._node_finalize)
        
        # Definir fluxo
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "plan")
        workflow.add_conditional_edges(
            "plan",
            self._should_execute,
            {
                "execute": "execute",
                "finalize": "finalize",
            }
        )
        workflow.add_edge("execute", "review")
        workflow.add_conditional_edges(
            "review",
            self._should_retry,
            {
                "execute": "execute",
                "finalize": "finalize",
            }
        )
        workflow.add_edge("finalize", END)
        
        self._graph = workflow.compile(checkpointer=self._checkpointer)
    
    def run(self, initial_state: dict[str, Any]) -> OrchestratorState:
        """
        Executa o orchestrator com estado inicial.
        
        Args:
            initial_state: Estado inicial da orquestração
            
        Returns:
            Estado final com resultados
        """
        state = OrchestratorState(
            project_id=self.config.project_id,
            tasks=[initial_state],
            current_phase="initializing",
        )
        
        # Executar graph
        config = {"configurable": {"thread_id": state.run_id}}
        final_state = self._graph.invoke(state, config)
        
        return final_state
    
    def run_async(self, initial_state: dict[str, Any]) -> str:
        """
        Executa assincronamente e retorna o run_id.
        Útil para dashboard real-time.
        """
        state = OrchestratorState(
            project_id=self.config.project_id,
            tasks=[initial_state],
            current_phase="initializing",
        )
        
        # TODO: Implementar execução async com threading
        # Por agora, retorna o run_id
        return state.run_id
    
    # ─── Nodes ───────────────────────────────────────────────────────────
    
    def _node_initialize(self, state: OrchestratorState) -> dict:
        """Nó de inicialização."""
        state.current_phase = "initializing"
        state.progress = 0
        
        # Emitir evento
        event = AgentEvent(
            agent_id="orchestrator",
            agent_role="coordinator",
            status=AgentStatus.RUNNING,
            task_id=state.run_id,
            project_id=state.project_id,
            message="Orchestrator inicializado",
        )
        self.notifier.emit(event)
        
        return {"current_phase": "initialized", "progress": 10}
    
    def _node_plan(self, state: OrchestratorState) -> dict:
        """Nó de planejamento — distribui tarefas."""
        state.current_phase = "planning"
        state.progress = 20
        
        # Emitir evento
        event = AgentEvent(
            agent_id="orchestrator",
            agent_role="coordinator",
            status=AgentStatus.RUNNING,
            task_id=state.run_id,
            project_id=state.project_id,
            message=f"Planejando execução de {len(state.tasks)} tarefa(s)",
            payload={"tasks": state.tasks},
        )
        self.notifier.emit(event)
        
        return {"current_phase": "planned", "progress": 30}
    
    def _node_execute(self, state: OrchestratorState) -> dict:
        """Nó de execução — roda os agentes."""
        state.current_phase = "executing"
        state.progress = 40
        
        # Executar cada tarefa
        for i, task in enumerate(state.tasks):
            agent_id = task.get("agent_id", "default")
            
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                result = agent.run(task)
                
                if result.status == AgentStatus.COMPLETED:
                    state.completed_tasks.append(task.get("task_id", f"task_{i}"))
                else:
                    state.failed_tasks.append(task.get("task_id", f"task_{i}"))
            
            # Atualizar progresso
            state.progress = 40 + (i + 1) / len(state.tasks) * 40
        
        return {
            "current_phase": "executed",
            "progress": 80,
            "completed_tasks": state.completed_tasks,
            "failed_tasks": state.failed_tasks,
        }
    
    def _node_review(self, state: OrchestratorState) -> dict:
        """Nó de revisão — verifica resultados."""
        state.current_phase = "reviewing"
        state.progress = 90
        
        # Verificar se todas as tarefas foram concluídas
        all_tasks = len(state.completed_tasks) + len(state.failed_tasks)
        success_rate = len(state.completed_tasks) / all_tasks if all_tasks > 0 else 0
        
        event = AgentEvent(
            agent_id="orchestrator",
            agent_role="coordinator",
            status=AgentStatus.RUNNING,
            task_id=state.run_id,
            project_id=state.project_id,
            message=f"Revisão: {success_rate:.0%} de sucesso",
            payload={
                "completed": len(state.completed_tasks),
                "failed": len(state.failed_tasks),
                "success_rate": success_rate,
            },
        )
        self.notifier.emit(event)
        
        return {"current_phase": "reviewed", "progress": 95}
    
    def _node_finalize(self, state: OrchestratorState) -> dict:
        """Nó de finalização."""
        state.current_phase = "completed"
        state.progress = 100
        
        # Determinar status final
        if state.failed_tasks and not state.completed_tasks:
            final_status = AgentStatus.FAILED
        elif state.failed_tasks:
            final_status = AgentStatus.COMPLETED  # Parcial
        else:
            final_status = AgentStatus.COMPLETED
        
        event = AgentEvent(
            agent_id="orchestrator",
            agent_role="coordinator",
            status=final_status,
            task_id=state.run_id,
            project_id=state.project_id,
            message="Orquestração concluída",
            payload={
                "completed_tasks": state.completed_tasks,
                "failed_tasks": state.failed_tasks,
            },
        )
        self.notifier.emit(event)
        
        # Enviar notificação Windows
        total_tasks = len(state.completed_tasks) + len(state.failed_tasks)
        completed = len(state.completed_tasks)
        failed = len(state.failed_tasks)
        
        # Calcular duração a partir dos eventos
        duration = 0.0
        if state.completed_tasks or state.failed_tasks:
            events = self.notifier.get_events()
            start_event = next((e for e in events if e.status == AgentStatus.RUNNING), None)
            end_event = next((e for e in reversed(events) if e.status in [AgentStatus.COMPLETED, AgentStatus.FAILED]), None)
            if start_event and end_event:
                try:
                    start_ts = start_event.timestamp.timestamp()
                    end_ts = end_event.timestamp.timestamp()
                    duration = end_ts - start_ts
                except:
                    pass
        
        if failed > 0:
            send_error_notification(
                state.project_id,
                f"{failed}/{total_tasks} tarefas falharam"
            )
        else:
            send_completion_notification(
                state.project_id,
                total_tasks,
                completed,
                failed,
                duration
            )
        
        return {"current_phase": "completed", "progress": 100}
    
    # ─── Conditional Edges ───────────────────────────────────────────────
    
    def _should_execute(self, state: OrchestratorState) -> Literal["execute", "finalize"]:
        """Decide se deve executar ou finalizar."""
        if state.tasks:
            return "execute"
        return "finalize"
    
    def _should_retry(self, state: OrchestratorState) -> Literal["execute", "finalize"]:
        """Decide se deve retry ou finalizar."""
        if state.failed_tasks and len(state.completed_tasks) == 0:
            # Todas falharam — finalizar com erro
            return "finalize"
        # Continuar (pode adicionar retry logic aqui)
        return "finalize"
