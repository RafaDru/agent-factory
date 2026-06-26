"""
Exemplo: Agent Orchestrator com Dashboard Real-Time
====================================================
Demonstra como usar o framework para criar e executar agentes
com dashboard atualizando em tempo real.
"""

import time
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    ProjectConfig,
    OrchestratorGraph,
    EventNotifier,
    DashboardServer,
    AgentBase,
    AgentRole,
)
from src.notifications.windows import send_windows_notification


# ─── Agentes de Exemplo ───────────────────────────────────────────────────

class DataFetcherAgent(AgentBase):
    """Agente que busca dados (simulado)."""
    
    def __init__(self, project_id: str, notifier: EventNotifier):
        super().__init__(
            agent_id="data-fetcher",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
        )
    
    def validate_input(self, task) -> bool:
        return "url" in task or "source" in task
    
    def execute(self, task) -> dict:
        # Simular busca de dados
        time.sleep(2)
        return {
            "records": 150,
            "source": task.get("source", "api"),
            "status": "fetched",
        }


class DataProcessorAgent(AgentBase):
    """Agente que processa dados (simulado)."""
    
    def __init__(self, project_id: str, notifier: EventNotifier):
        super().__init__(
            agent_id="data-processor",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
        )
    
    def validate_input(self, task) -> bool:
        return "data" in task
    
    def execute(self, task) -> dict:
        # Simular processamento
        time.sleep(3)
        data = task.get("data", {})
        return {
            "processed": data.get("records", 0),
            "output_file": "output/processed.json",
            "status": "processed",
        }


class ReportGeneratorAgent(AgentBase):
    """Agente que gera relatório (simulado)."""
    
    def __init__(self, project_id: str, notifier: EventNotifier):
        super().__init__(
            agent_id="report-generator",
            project_id=project_id,
            notifier=notifier,
            role=AgentRole.WORKER,
        )
    
    def validate_input(self, task) -> bool:
        return True
    
    def execute(self, task) -> dict:
        # Simular geração de relatório
        time.sleep(2)
        return {
            "report_file": "output/report.html",
            "summary": "Relatório gerado com sucesso",
            "status": "generated",
        }


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    print("Agent Orchestrator - Exemplo com Dashboard")
    print("=" * 50)
    
    # 1. Configurar projeto
    config = ProjectConfig(
        project_id="example-project",
        name="Projeto de Exemplo",
        description="Demonstração do Agent Orchestrator",
        dashboard_port=8080,
    )
    
    # 2. Criar notifier
    notifier = EventNotifier(config.project_id)
    
    # 3. Iniciar dashboard
    server = DashboardServer(notifier, port=config.dashboard_port)
    server.start()
    
    print(f"\nDashboard rodando em: http://localhost:{config.dashboard_port}")
    print("   Abra no navegador para acompanhar em tempo real\n")
    
    # 4. Criar agentes
    fetcher = DataFetcherAgent(config.project_id, notifier)
    processor = DataProcessorAgent(config.project_id, notifier)
    reporter = ReportGeneratorAgent(config.project_id, notifier)
    
    # 5. Criar orchestrator e registrar agentes
    orchestrator = OrchestratorGraph(config)
    orchestrator.add_agent(fetcher)
    orchestrator.add_agent(processor)
    orchestrator.add_agent(reporter)
    
    # 6. Executar pipeline
    print("\nIniciando execucao...\n")
    
    start_time = time.time()
    
    # Executar cada agente sequencialmente
    # (em produção, usar LangGraph para orquestração complexa)
    
    # Passo 1: Buscar dados
    result1 = fetcher.run({
        "task_id": "fetch-1",
        "source": "api-exemplo",
    })
    print(f"OK Data Fetcher: {result1.status.value}")
    
    # Passo 2: Processar dados
    result2 = processor.run({
        "task_id": "process-1",
        "data": result1.output,
    })
    print(f"OK Data Processor: {result2.status.value}")
    
    # Passo 3: Gerar relatório
    result3 = reporter.run({
        "task_id": "report-1",
        "data": result2.output,
    })
    print(f"OK Report Generator: {result3.status.value}")
    
    # 7. Finalizar
    total_time = time.time() - start_time
    
    print(f"\nExecucao concluida em {total_time:.1f}s")
    print(f"   Dashboard: http://localhost:{config.dashboard_port}")
    
    # 8. Enviar notificação Windows
    send_windows_notification(
        title="Agent Orchestrator - Exemplo Concluido",
        message=f"Pipeline executado com sucesso em {total_time:.1f}s",
        duration="long",
    )
    
    # Manter server rodando
    print("Pressione Ctrl+C para encerrar...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando...")
        server.stop()


if __name__ == "__main__":
    main()
