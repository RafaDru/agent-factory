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

    # Register all projects — output_dir matches EventNotifier convention
    projects = {
        "agent-factory-dev": ".agent-factory/events",
        "pta": ".agent-factory/events",
    }

    server = None
    af_notifier = None

    for proj, output_dir in projects.items():
        notifier = EventNotifier(proj, output_dir=output_dir)
        store = ContextStore(proj)

        # Load existing events from disk
        events_file = Path(output_dir) / proj / "events.jsonl"
        if events_file.exists():
            try:
                with open(events_file, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            from src.protocols.schema import AgentEvent
                            import json
                            data = json.loads(line)
                            event = AgentEvent(**data)
                            notifier._events.append(event)
            except Exception:
                pass

        if server is None:
            server = DashboardServer(notifier, port=port, context_store=store)
            af_notifier = notifier
        else:
            server.add_notifier(notifier)
            server.add_context_store(proj, store)

        print(f"\n  [{proj}] {output_dir}/events/")

    print(f"\n[Dashboard] http://localhost:{port}")
    print(f"[Dashboard] Projetos: {list(projects.keys())}")

    # Start server in a thread
    import threading
    t = threading.Thread(target=server.start, daemon=True)
    t.start()
    time.sleep(0.5)

    if demo and af_notifier:
        run_demo_agents(af_notifier)

    print(f"\n{'─' * 50}")
    print("Agent Factory pronto! Pressione Ctrl+C para encerrar.")
    print(f"{'─' * 50}")

    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando Agent Factory...")


def run_demo_agents(notifier):
    """Run demo agents to populate the dashboard."""
    from src.protocols.schema import AgentEvent, AgentStatus, AgentRole

    print("\n[Demo] 🎬 Executando agentes de demonstração...")

    events_data = [
        ("coordenador", AgentRole.COORDINATOR, AgentStatus.RUNNING,
         "Iniciando pipeline de desenvolvimento"),
        ("agent-factory-dev", AgentRole.WORKER, AgentStatus.RUNNING,
         "Analisando estrutura do framework"),
        ("qa", AgentRole.WORKER, AgentStatus.RUNNING,
         "Verificando dependências do projeto"),
    ]
    for agent_id, role, status, message in events_data:
        notifier.emit(AgentEvent(
            agent_id=agent_id, agent_role=role, status=status,
            task_id="startup", project_id="agent-factory-dev",
            message=message,
            metrics={"duration_seconds": 0, "context": {
                "used_kb": 2.4, "limit_kb": 15.0, "tokens": 214,
                "token_limit": 32000, "percentage": 6.9,
                "status": "ok", "compressing": False,
            }},
        ))
        time.sleep(1)

    notifier.emit(AgentEvent(
        agent_id="coordenador", agent_role=AgentRole.COORDINATOR,
        status=AgentStatus.COMPLETED, task_id="startup",
        project_id="agent-factory-dev",
        message="Ambiente local configurado — squad multi-modelo disponível",
        metrics={"duration_seconds": 3.2, "context": {
            "used_kb": 3.1, "limit_kb": 15.0, "tokens": 312,
            "token_limit": 32000, "percentage": 10.0,
            "status": "ok", "compressing": False,
        }},
    ))

    print("[Demo] ✅ Agentes de demonstração executados")


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
