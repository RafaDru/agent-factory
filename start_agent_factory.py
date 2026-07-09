"""
Agent Factory — Startup Script
================================
Entry point cross-platform. Inicia Ollama (se necessário),
configura GPU, sobe o Dashboard, e mantém o ambiente ativo.

Uso:
    python start_agent_factory.py              # modo normal
    python start_agent_factory.py --demo       # + demo agents
    python start_agent_factory.py --no-ollama  # não gerencia Ollama
    python start_agent_factory.py --port 9090  # porta customizada
"""

import sys
import time
import json
import os
import subprocess
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# Ensure project root is in path
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

DASHBOARD_PORT = 8080
OLLAMA_HOST = "http://localhost:11434"

# GPU optimization env vars for Ollama
OLLAMA_ENV = {
    "OLLAMA_FLASH_ATTENTION": "1",
    "OLLAMA_KV_CACHE_TYPE": "q8_0",
    "OLLAMA_NUM_PARALLEL": "2",
    "OLLAMA_MAX_LOADED_MODELS": "3",
    "OLLAMA_SCHED_SPREAD": "1",
    "OLLAMA_KEEP_ALIVE": "15m",
}


def print_banner():
    print("""
    +----------------------------------------------+
    |        Agent Factory -- v2.0.0-beta           |
    |    Local Multi-Model Squad Ready              |
    +----------------------------------------------+
    """)


def find_ollama() -> str | None:
    """Find ollama binary in PATH or common locations."""
    try:
        import shutil
        return shutil.which("ollama")
    except Exception:
        pass
    # Common locations per platform
    candidates = [
        "/usr/local/bin/ollama",
        "/usr/bin/ollama",
        os.path.expanduser("~/ollama"),
        r"C:\Program Files\Ollama\ollama.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe"),
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def is_ollama_running() -> bool:
    """Check if Ollama server is responding."""
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def start_ollama():
    """Start Ollama with GPU optimizations."""
    ollama_path = find_ollama()
    if not ollama_path:
        print("[Ollama] ❌ Binário não encontrado. Instale: https://ollama.com")
        return False

    if is_ollama_running():
        print("[Ollama] ✅ Já está rodando")
        return True

    print("[Ollama] 🚀 Iniciando com otimizações GPU...")
    for k, v in OLLAMA_ENV.items():
        os.environ[k] = v
        print(f"         {k}={v}")

    try:
        if sys.platform == "win32":
            subprocess.Popen(
                [ollama_path, "serve"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        # Wait for startup
        for i in range(15):
            if is_ollama_running():
                print(f"[Ollama] ✅ Rodando em {OLLAMA_HOST}")
                return True
            time.sleep(1)
        print("[Ollama] ⚠️  Timeout — pode já estar iniciando em segundo plano")
        return False
    except Exception as e:
        print(f"[Ollama] ❌ Erro ao iniciar: {e}")
        return False


def list_ollama_models():
    """List installed Ollama models."""
    try:
        resp = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5)
        data = json.loads(resp.read())
        models = data.get("models", [])
        if models:
            print(f"\n[Modelos] {len(models)} disponíveis:")
            for m in sorted(models, key=lambda x: -x["size"]):
                name = m["name"]
                size_gb = m["size"] / (1024 ** 3)
                print(f"  • {name:<25s} ({size_gb:.1f} GB)")
        else:
            print("\n[Modelos] ⚠️  Nenhum modelo instalado. Execute:")
            print("         ollama pull gemma3:4b")
            print("         ollama pull qwen2.5-coder:7b")
            print("         ollama pull qwen3.6")
            print("         ollama pull gemma4")
        return models
    except Exception as e:
        print(f"\n[Modelos] ⚠️  Não foi possível listar: {e}")
        return []


def start_dashboard(port: int, demo: bool = False):
    """Start the Dashboard server with multi-project support."""
    from src.protocols.events import EventNotifier
    from src.dashboard.server import DashboardServer
    from src.persistence import ContextStore
    from src.registry import get_registry
    from src.loader import AgentReference
    from src.protocols.schema import ProjectConfig

    registry = get_registry()

    # Register agent-factory-dev project
    if not registry.project_exists("agent-factory-dev"):
        registry.register(ProjectConfig(
            project_id="agent-factory-dev",
            name="Agent Factory",
            description="Plataforma de orquestracao de agentes autonomos",
        ))

    # Register PTA project
    if not registry.project_exists("pta"):
        registry.register(ProjectConfig(
            project_id="pta",
            name="Personal Trainer Agent",
            description="App mobile com IA e visao computacional",
        ))

    # Register real agent references for agent-factory-dev project
    agent_src = Path(__file__).parent / "src" / "agents"
    ctx_base = Path(__file__).parent / "contexts" / "agent-factory-dev"
    refs = [
        AgentReference(
            agent_id="coordenador",
            module_path=str(agent_src / "coordinator.py"),
            class_name="AgentFactoryCoordinator",
            context_limit_kb=15.0,
            context_file=str(ctx_base / "coordenador" / "CONTEXTO.md"),
        ),
        AgentReference(
            agent_id="agent-factory-dev",
            module_path=str(agent_src / "factory_dev.py"),
            class_name="AgentFactoryDevAgent",
            context_limit_kb=15.0,
            context_file=str(ctx_base / "agent-factory-dev" / "CONTEXTO.md"),
        ),
        AgentReference(
            agent_id="qa",
            module_path=str(agent_src / "qa.py"),
            class_name="QAAgent",
            context_limit_kb=10.0,
            context_file=str(ctx_base / "qa" / "CONTEXTO.md"),
        ),
    ]
    for ref in refs:
        registry.add_agent_ref("agent-factory-dev", ref)

    # Register PTA agent refs if not already there
    pta_agent_path = Path.home() / "PersonalTrainerAgent" / "agentes" / "__init__.py"
    if pta_agent_path.exists() and not registry.list_agent_refs("pta"):
        pta_refs = [
            AgentReference(agent_id="coordenador", module_path=str(pta_agent_path), class_name="CoordenadorAgent"),
            AgentReference(agent_id="frontend-mobile", module_path=str(pta_agent_path), class_name="FrontendMobileAgent"),
            AgentReference(agent_id="visao-computacional", module_path=str(pta_agent_path), class_name="VisaoComputacionalAgent"),
            AgentReference(agent_id="ui-ux", module_path=str(pta_agent_path), class_name="UIUXAgent"),
            AgentReference(agent_id="qa", module_path=str(pta_agent_path), class_name="QAAgent"),
            AgentReference(agent_id="renderizacao", module_path=str(pta_agent_path), class_name="RenderizacaoAgent"),
            AgentReference(agent_id="agent-factory-dev", module_path=str(pta_agent_path), class_name="AgentFactoryDevAgent"),
            AgentReference(agent_id="research", module_path=str(pta_agent_path), class_name="ResearchAgent"),
        ]
        for ref in pta_refs:
            registry.add_agent_ref("pta", ref)

    # Build dashboard server with notifiers from registry
    server = None
    af_notifier = None
    projects = registry.list_project_ids()

    for proj in projects:
        notifier = registry.get_notifier(proj)
        store = ContextStore(proj)

        if server is None:
            server = DashboardServer(notifier, port=port, context_store=store)
            af_notifier = notifier
        else:
            server.add_notifier(notifier)
            server.add_context_store(proj, store)

        print(f"\n  [{proj}] eventos em: .agent-factory/events/{proj}/")

    print(f"\n[Dashboard] http://localhost:{port}")
    print(f"[Dashboard] Projetos: {projects}")

    # Start server in a thread
    import threading
    t = threading.Thread(target=server.start, daemon=True)
    t.start()
    time.sleep(0.5)

    if demo and af_notifier:
        run_demo_agents(registry)

    print(f"\n{'─' * 50}")
    print("Agent Factory pronto! Pressione Ctrl+C para encerrar.")
    print(f"{'─' * 50}")

    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando Agent Factory...")


def run_demo_agents(registry):
    """Load and run real agents to populate the dashboard with live events."""
    from src.protocols.schema import AgentEvent, AgentStatus, AgentRole

    print("\n[Demo] 🎬 Carregando agentes reais...")

    project_id = "agent-factory-dev"

    # Load agents from registry (this triggers real imports)
    try:
        coordenador = registry.load_agent(project_id, "coordenador")
        dev_agent = registry.load_agent(project_id, "agent-factory-dev")
        qa_agent = registry.load_agent(project_id, "qa")
    except Exception as e:
        print(f"[Demo] ⚠️  Erro ao carregar agentes: {e}")
        print("[Demo] → Usando fallback com eventos diretos")
        _demo_fallback(registry.get_notifier(project_id))
        return

    # Wire subordinates
    coordenador.set_subordinates({
        "agent-factory-dev": dev_agent,
        "qa": qa_agent,
    })

    print("[Demo] ✅ Agentes carregados. Executando tarefas...")

    # Task 1: agent-factory-dev lists its own capabilities
    result1 = dev_agent.run({
        "task_id": "startup-capabilities",
        "title": "Capabilities",
        "action": "get_capabilities",
    })
    print(f"  [agent-factory-dev] capabilities: {result1.status.value}")

    # Task 2: QAAgent validates syntax of a core file
    core_file = str(Path(__file__).parent / "src" / "agents" / "base.py")
    result2 = qa_agent.run({
        "task_id": "startup-validate",
        "title": "Validacao Inicial",
        "description": "Validar sintaxe do AgentBase",
        "action": "validate_python_syntax",
        "file_path": core_file,
    })
    print(f"  [qa] validacao: {result2.status.value}")

    # Task 3: Coordenador delegates a plan
    result3 = coordenador.run({
        "task_id": "startup-plan",
        "title": "Plano Inicial",
        "action": "plan_and_execute",
        "goal": "Validar ambiente de desenvolvimento Agent Factory",
        "tasks": [
            {
                "name": "list-src",
                "agent_id": "agent-factory-dev",
                "task": {
                    "task_id": "step-list",
                    "action": "list_directory",
                    "path": str(Path(__file__).parent / "src"),
                    "pattern": "**/*.py",
                },
            },
            {
                "name": "run-tests",
                "agent_id": "qa",
                "task": {
                    "task_id": "step-tests",
                    "action": "run_tests",
                    "path": "tests/",
                    "args": ["--tb=short", "-q"],
                },
                "depends_on": ["list-src"],
            },
        ],
    })
    print(f"  [coordenador] plano: {result3.output.get('status', '?')}")

    print("[Demo] ✅ Agentes reais executados com sucesso")


def _demo_fallback(notifier):
    """Fallback: emite eventos diretos se o loading de agentes falhar."""
    from src.protocols.schema import AgentEvent, AgentStatus, AgentRole

    print("[Demo] → Fallback: emitindo eventos simulados")

    for agent_id, role, msg in [
        ("coordenador", AgentRole.COORDINATOR, "Iniciando pipeline"),
        ("agent-factory-dev", AgentRole.WORKER, "Analisando estrutura"),
        ("qa", AgentRole.WORKER, "Verificando dependencias"),
    ]:
        notifier.emit(AgentEvent(
            agent_id=agent_id, agent_role=role,
            status=AgentStatus.RUNNING, task_id="startup",
            project_id="agent-factory-dev", message=msg,
        ))
        time.sleep(1)

    for agent_id, msg in [
        ("coordenador", "Ambiente configurado"),
        ("agent-factory-dev", "Estrutura analisada"),
        ("qa", "Dependencias OK"),
    ]:
        notifier.emit(AgentEvent(
            agent_id=agent_id, agent_role=AgentRole.WORKER,
            status=AgentStatus.COMPLETED, task_id="startup",
            project_id="agent-factory-dev", message=msg,
        ))
        time.sleep(1)

    print("[Demo] ✅ Fallback concluido")


def main():
    parser = argparse.ArgumentParser(description="Agent Factory Startup")
    parser.add_argument("--port", type=int, default=DASHBOARD_PORT,
                        help=f"Dashboard port (default: {DASHBOARD_PORT})")
    parser.add_argument("--demo", action="store_true",
                        help="Run demo agents on startup")
    parser.add_argument("--no-ollama", action="store_true",
                        help="Skip Ollama management")
    args = parser.parse_args()

    print_banner()

    # Step 1: Ollama
    if not args.no_ollama:
        start_ollama()
        list_ollama_models()
    else:
        print("[Ollama] ⏭️  Gerenciamento desabilitado (--no-ollama)")

    # Step 2: Dashboard (blocking)
    start_dashboard(port=args.port, demo=args.demo)


if __name__ == "__main__":
    main()
