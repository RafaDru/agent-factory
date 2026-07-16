"""
Agent Factory — Dashboard Server
==================================
Server HTTP simples para dashboard com suporte a SSE e REST API.
Gerencia múltiplos projetos, agentes e eventos em tempo real.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Any, Dict, List
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

from ..protocols.events import EventNotifier
from ..registry import get_registry

CONFIG_FILE = '.agent-factory/agent_config.json'
agent_config: Dict[str, Dict[str, str]] = {}

def load_config() -> None:
    """Carrega a configuração de agentes do arquivo JSON."""
    global agent_config
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                agent_config = json.load(f)
        else:
            agent_config = {}
    except (json.JSONDecodeError, IOError):
        agent_config = {}

def save_config() -> None:
    """Salva a configuração de agentes no arquivo JSON."""
    global agent_config
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(agent_config, f, indent=2)

# Carrega a configuração ao iniciar o módulo
load_config()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer com suporte a múltiplas threads para melhor performance."""
    daemon_threads = True

class DashboardHandler(SimpleHTTPRequestHandler):
    """
    Handler HTTP para o dashboard da Agent Factory Platform.
    Gerencia requisições para o dashboard e todos os endpoints da API.
    """

    # Variáveis de classe compartilhadas entre todas as instâncias
    notifiers: Dict[str, EventNotifier] = {}
    context_stores: Dict[str, Any] = {}
    agent_providers: Dict[str, str] = {}  # agent_id → "local_multi" | "cloud" | "auto"

    def do_GET(self) -> None:
        """Roteia requisições GET para os endpoints apropriados."""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        project_id = params.get("project", [None])[0]

        # Roteamento de endpoints
        if path in ("/", "/index.html"):
            self._serve_dashboard()
        elif path == "/api/events":
            self._serve_events(project_id)
        elif path == "/api/events/stream":
            self._serve_events_sse()
        elif path == "/api/status":
            self._serve_status(project_id)
        elif path == "/api/context":
            self._serve_context(project_id)
        elif path == "/api/projects":
            self._serve_projects()
        elif path == "/api/missions":
            self._serve_missions()
        elif path == "/api/agent-config":
            self._serve_agent_config()
        elif path == "/api/debug":
            self._serve_debug()
        elif path.startswith("/api/agent/") and path.endswith("/provider"):
            self._serve_agent_provider(path)
        else:
            self.send_error(404, "Endpoint não encontrado")

    def do_POST(self) -> None:
        """Roteia requisições POST para os endpoints apropriados."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/agent-config":
            self._post_agent_config()
        elif path.startswith("/api/agent/") and path.endswith("/provider"):
            self._post_agent_provider(path)
        else:
            self.send_error(404, "Endpoint POST não encontrado")

    def log_message(self, format: str, *args: Any) -> None:
        """Suprime logs padrão do servidor para reduzir poluição no console."""
        # Logs podem ser habilitados para debug se necessário
        pass

    def _serve_dashboard(self) -> None:
        """Serve o HTML do dashboard principal.

        Returns:
            None: Envia a resposta HTTP com o conteúdo do dashboard
        """
        dashboard_path = Path(__file__).parent / "index.html"
        if dashboard_path.exists():
            try:
                with open(dashboard_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.send_error(500, f"Erro ao ler dashboard: {str(e)}")
        else:
            self.send_error(404, "Dashboard não encontrado")

    def _get_notifier(self, project_id: Optional[str] = None) -> Optional[EventNotifier]:
        """Obtém o EventNotifier para um projeto específico.

        Args:
            project_id: ID do projeto. Se None, tenta obter qualquer notifier disponível.

        Returns:
            EventNotifier: Instância do notifier ou None se não encontrado
        """
        if project_id and project_id in self.notifiers:
            return self.notifiers[project_id]

        # Fallback para projetos únicos
        if len(self.notifiers) == 1:
            return next(iter(self.notifiers.values()))

        return None

    def _get_context_store(self, project_id: Optional[str] = None) -> Optional[Any]:
        """Obtém o ContextStore para um projeto específico.

        Args:
            project_id: ID do projeto. Se None, tenta obter qualquer store disponível.

        Returns:
            ContextStore: Instância do store ou None se não encontrado
        """
        if project_id and project_id in self.context_stores:
            return self.context_stores[project_id]

        # Fallback para projetos únicos
        if len(self.context_stores) == 1:
            return next(iter(self.context_stores.values()))

        return None

    def _serve_events(self, project_id: Optional[str] = None) -> None:
        """Endpoint REST para obter eventos como JSON.

        Args:
            project_id: ID do projeto para filtrar eventos

        Returns:
            None: Envia resposta com eventos e configurações de provedores
        """
        # Obter notifiers apropriados
        if project_id:
            notifier = self._get_notifier(project_id)
            notifiers = [notifier] if notifier else []
        else:
            notifiers = list(self.notifiers.values())

        # Coletar todos os eventos
        all_events = []
        for n in notifiers:
            try:
                evts = n.get_events()
                all_events.extend(evts)
            except Exception as e:
                print(f"[Dashboard] Erro ao ler eventos de {n.project_id}: {e}")

        # Ordenar por timestamp (mais recente primeiro)
        all_events.sort(key=lambda e: e.timestamp, reverse=True)

        # Extrair modelo do LLM de cada agente
        agent_models: Dict[str, str] = {}
        for e in reversed(all_events):
            aid = e.agent_id
            if aid not in agent_models:
                # Tentar obter modelo das métricas
                m = e.metrics.get("model") if e.metrics else None
                if m:
                    agent_models[aid] = m
                # Tentar obter modelo do payload
                elif e.payload and isinstance(e.payload, dict):
                    m = e.payload.get("model") or e.payload.get("provider_model")
                    if m:
                        agent_models[aid] = m

        # Construir resposta
        result = {
            "events": [e.model_dump(mode="json") for e in all_events],
            "providers": dict(self.agent_providers),
            "agent_models": agent_models,
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result, default=str).encode("utf-8"))

    def _serve_events_sse(self) -> None:
        """Endpoint SSE para transmissão de eventos em tempo real.

        Returns:
            None: Mantém conexão aberta e envia eventos conforme ocorrem
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Registrar cliente SSE
        EventNotifier.register_sse_client(self)

        try:
            # Manter conexão aberta
            while True:
                time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            # Cliente desconectou
            pass
        finally:
            # Desregistrar cliente SSE
            EventNotifier.unregister_sse_client(self)

    def _serve_status(self, project_id: Optional[str] = None) -> None:
        """Endpoint para obter status atual do projeto.

        Args:
            project_id: ID do projeto

        Returns:
            None: Envia resposta com status do projeto
        """
        notifier = self._get_notifier(project_id)
        if notifier:
            data = notifier.get_status()
        else:
            data = {
                "project_id": project_id,
                "phase": "unknown",
                "progress": 0
            }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _serve_context(self, project_id: Optional[str] = None) -> None:
        """Endpoint para obter métricas de contexto dos agentes.

        Args:
            project_id: ID do projeto

        Returns:
            None: Envia resposta com métricas de contexto
        """
        store = self._get_context_store(project_id)
        notifier = self._get_notifier(project_id)
        data = {"agents": {}, "project": project_id or "unknown"}

        def _get_entry(agent_id: str) -> Dict[str, Any]:
            """Helper para obter dados de contexto de um agente específico."""
            entry = {}

            # File-based context from CONTEXTO.md
            if project_id:
                context_file = Path("contexts") / project_id / agent_id / "CONTEXTO.md"
                if context_file.exists():
                    size = context_file.stat().st_size
                    entry["has_context"] = True
                    entry["context_size_bytes"] = size
                    entry["context_pct"] = min(100.0, round((size / 10240) * 100, 1))
                else:
                    entry["has_context"] = False
                    entry["context_size_bytes"] = 0
                    entry["context_pct"] = 0.0
            else:
                entry["has_context"] = False
                entry["context_size_bytes"] = 0
                entry["context_pct"] = 0.0

            # Additional data from store if available
            if store:
                try:
                    agent_events_store = store.get_agent_history(agent_id, limit=10000)
                    entry["events"] = len(agent_events_store)
                    entry["last_event"] = agent_events_store[0]["timestamp"] if agent_events_store else None
                except Exception:
                    pass

            # Context tracking from events
            if notifier:
                for event in reversed(notifier.get_events()):
                    if event.agent_id == agent_id and event.metrics.get("context"):
                        entry["context_tracking"] = event.metrics["context"]
                        break

            return entry

        # Listar IDs dos agentes
        agent_ids = self._list_agent_ids(project_id)

        # Adicionar estatísticas do projeto se não houver agentes específicos
        if not agent_ids and store:
            try:
                stats = store.get_stats()
                data["project_stats"] = stats
            except Exception:
                pass

        # Coletar dados de cada agente
        for agent_id in agent_ids:
            data["agents"][agent_id] = _get_entry(agent_id)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _serve_agent_config(self) -> None:
        """Endpoint GET para obter configuração de LLM de um agente."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        agent_id = params.get("agent_id", [None])[0]

        if not agent_id:
            self.send_error(400, "Parâmetro agent_id é obrigatório")
            return

        config = agent_config.get(agent_id, {"llm_provider": "AUTO"})

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(config).encode("utf-8"))

    def _post_agent_config(self) -> None:
        """Endpoint POST para atualizar configuração de LLM de um agente."""
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            self.send_error(400, "Corpo da requisição é obrigatório")
            return

        try:
            body = json.loads(self.rfile.read(content_len))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return

        agent_id = body.get("agent_id")
        llm_provider = body.get("llm_provider")

        if not agent_id or not llm_provider:
            self.send_error(400, "Campos agent_id e llm_provider são obrigatórios")
            return

        global agent_config
        agent_config[agent_id] = {"llm_provider": llm_provider}
        save_config()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "agent_id": agent_id,
            "llm_provider": llm_provider
        }).encode("utf-8"))


    def _list_agent_ids(self, project_id: Optional[str] = None) -> List[str]:
        """Lista IDs de todos os agentes de um projeto.

        Args:
            project_id: ID do projeto

        Returns:
            List[str]: Lista de IDs dos agentes
        """
        notifier = self._get_notifier(project_id)
        if not notifier:
            return []

        seen = set()
        for event in notifier.get_events():
            seen.add(event.agent_id)

        # Fallback: ler diretórios do filesystem para agentes com CONTEXTO.md
        contexts_dir = Path('contexts') / project_id
        if contexts_dir.exists():
            for d in contexts_dir.iterdir():
                if d.is_dir() and (d / 'CONTEXTO.md').exists():
                    seen.add(d.name)

        return sorted(seen)

    def _serve_agent_provider(self, path: str) -> None:
        """Endpoint para obter o provider configurado de um agente.

        Args:
            path: URL path da requisição

        Returns:
            None: Envia resposta com configuração do provider
        """
        import re
        m = re.match(r"/api/agent/(.+)/provider", path)
        if not m:
            self.send_error(400, "Path inválido")
            return

        agent_id = m.group(1)
        provider = self.agent_providers.get(agent_id, "auto")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "agent_id": agent_id,
            "provider": provider
        }).encode("utf-8"))

    def _post_agent_provider(self, path: str) -> None:
        """Endpoint para atualizar o provider de um agente.

        Args:
            path: URL path da requisição

        Returns:
            None: Envia resposta com confirmação da atualização
        """
        import re
        m = re.match(r"/api/agent/(.+)/provider", path)
        if not m:
            self.send_error(400, "Path inválido")
            return

        agent_id = m.group(1)

        # Validar e parsear body
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            self.send_error(400, "Corpo da requisição é obrigatório")
            return

        try:
            body = json.loads(self.rfile.read(content_len))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return

        provider = body.get("provider", "auto")
        valid_providers = ("auto", "local_multi", "cloud")

        if provider not in valid_providers:
            self.send_error(400, f"Provider inválido. Opções válidas: {valid_providers}")
            return

        # Atualizar provider
        previous_provider = self.agent_providers.get(agent_id, "auto")
        self.agent_providers[agent_id] = provider

        # Responder com confirmação
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "agent_id": agent_id,
            "provider": provider,
            "previous": previous_provider,
        }).encode("utf-8"))

    def _serve_projects(self) -> None:
        """Endpoint para listar todos os projetos com seus metadados.

        Returns:
            None: Envia resposta com lista de projetos
        """
        projects = []

        for pid in self.notifiers.keys():
            meta = {
                "project_id": pid,
                "project_name": pid,
                "team_name": pid,
                "icon": "📦",
                "agent_emojis": {},
            }

            # Tentar carregar metadados do projeto
            proj_json = Path("contexts") / pid / "project.json"
            if proj_json.exists():
                try:
                    data = json.loads(proj_json.read_text(encoding="utf-8"))

                    meta.update({
                        "project_name": data.get("project_name", pid),
                        "team_id": data.get("team_id", pid),
                        "team_name": data.get("team_name", data.get("project_name", pid)),
                        "description": data.get("description", ""),
                        "icon": data.get("icon", "📦"),
                        "working_dir": data.get("working_dir", ""),
                        "agents_source": data.get("agents_source", ""),
                        "agents": data.get("agents", []),
                    })

                    # Mapear emojis dos agentes
                    for a in data.get("agents", []):
                        if "agent_id" in a and "emoji" in a:
                            meta["agent_emojis"][a["agent_id"]] = a["emoji"]

                except Exception as e:
                    print(f"[Dashboard] Erro ao ler projeto {pid}: {e}")

            projects.append(meta)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(projects, ensure_ascii=False).encode("utf-8"))

    def _serve_missions(self) -> None:
        """Endpoint para listar todas as missões ativas com seu progresso.

        Returns:
            None: Envia resposta com lista de missões
        """
        missions_dir = Path(".agent-factory") / "missions"
        missions = []

        if missions_dir.exists():
            for mission_dir in sorted(missions_dir.iterdir(), reverse=True):
                if not mission_dir.is_dir() or mission_dir.name.startswith("_"):
                    continue

                # Contar tasks e coletar status
                tasks_out = mission_dir / "output" / "tasks"
                task_count = 0
                task_statuses = []

                if tasks_out.exists():
                    for task_dir in sorted(tasks_out.iterdir()):
                        if task_dir.is_dir():
                            task_count += 1

                            # Verificar status de cada agente na task
                            for agent_dir in task_dir.iterdir():
                                if agent_dir.is_dir():
                                    result = agent_dir / "result.md"
                                    if result.exists():
                                        txt = result.read_text(encoding="utf-8")
                                        if "**Status:** success" in txt:
                                            st = "completed"
                                        elif "**Status:** failure" in txt:
                                            st = "failed"
                                        else:
                                            st = "pending"

                                        task_statuses.append({
                                            "task": task_dir.name,
                                            "agent": agent_dir.name,
                                            "status": st,
                                        })

                # Calcular estatísticas
                completed = sum(1 for t in task_statuses if t["status"] == "completed")
                failed = sum(1 for t in task_statuses if t["status"] == "failed")

                # Extrair objetivo da missão
                ctx_path = mission_dir / "input" / "Mission_Context.md"
                objective = ""

                if ctx_path.exists():
                    content = ctx_path.read_text(encoding="utf-8")
                    lines = content.split("\n")

                    # Procurar pela seção de objetivo
                    for i, line in enumerate(lines):
                        if line.startswith("## Objetivo Cur"):
                            # Pegar as próximas linhas até próxima seção
                            j = i + 1
                            while j < len(lines) and not lines[j].startswith("##"):
                                if lines[j].strip():
                                    objective += lines[j] + "\n"
                                j += 1
                            break

                missions.append({
                    "id": mission_dir.name,
                    "objective": objective.strip()[:200],  # Limitar a 200 caracteres
                    "task_count": task_count,
                    "completed": completed,
                    "failed": failed,
                    "task_statuses": task_statuses,
                })

        data = {
            "missions": missions,
            "total": len(missions),
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    def _serve_debug(self) -> None:
        """Endpoint de debug para informações internas do servidor.

        Returns:
            None: Envia resposta com informações de debug
        """
        info = {}

        for key, n in self.notifiers.items():
            try:
                evts = n.get_events()
                info[key] = {
                    "event_count": len(evts),
                    "file": str(n._events_file),
                    "file_exists": n._events_file.exists()
                }
            except Exception as e:
                info[key] = {
                    "error": str(e),
                    "file": str(n._events_file)
                }

        data = {
            "notifier_keys": list(self.notifiers.keys()),
            "notifier_count": len(self.notifiers),
            "details": info,
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

class DashboardServer:
    """
    Servidor principal do dashboard da Agent Factory Platform.

    Responsável por iniciar e gerenciar o servidor HTTP que serve:
    - O dashboard HTML
    - Todos os endpoints da API REST
    - O endpoint SSE para eventos em tempo real

    Exemplo de uso:
        notifier = EventNotifier("my-project")
        server = DashboardServer(notifier, port=8080)
        server.start()
    """

    def __init__(
        self,
        notifier: Optional[EventNotifier] = None,
        port: int = 8080,
        host: str = "localhost",
        context_store: Optional[Any] = None,
    ):
        """Inicializa o servidor do dashboard.

        Args:
            notifier: (deprecated — ignorado, usa registry)
            port: Porta para o servidor HTTP
            host: Host para o servidor HTTP
            context_store: Instância de ContextStore opcional
        """
        self.port = port
        self.host = host
        self._server: Optional[HTTPServer] = None

        # Obter notifiers do registry (compartilhado com missoes)
        registry = get_registry()
        for pid in registry.list_project_ids():
            n = registry.get_notifier(pid)
            if n:
                DashboardHandler.notifiers[n.project_id] = n

        # Registrar context store se fornecida
        if context_store:
            # Se houver apenas um notifier, associar ao seu project_id
            if len(DashboardHandler.notifiers) == 1:
                pid = next(iter(DashboardHandler.notifiers.keys()))
                DashboardHandler.context_stores[pid] = context_store

    def add_notifier(self, notifier: EventNotifier) -> None:
        """Adiciona um novo EventNotifier para outro projeto.

        Args:
            notifier: Instância de EventNotifier a ser adicionada
        """
        DashboardHandler.notifiers[notifier.project_id] = notifier

    def add_context_store(self, project_id: str, context_store: Any) -> None:
        """Adiciona um novo ContextStore para um projeto.

        Args:
            project_id: ID do projeto
            context_store: Instância de ContextStore a ser adicionada
        """
        DashboardHandler.context_stores[project_id] = context_store

    def start(self) -> None:
        """Inicia o servidor HTTP.

        O servidor ficará em execução até ser interrompido.
        """
        self._server = ThreadingHTTPServer((self.host, self.port), DashboardHandler)

        print(f"Dashboard: http://{self.host}:{self.port}")
        print(f"Projetos ativos: {list(DashboardHandler.notifiers.keys())}")

        if DashboardHandler.context_stores:
            print(f"ContextStores ativos: {list(DashboardHandler.context_stores.keys())}")

        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server interrompido pelo usuário")
        finally:
            self.stop()

    def stop(self) -> None:
        """Para o servidor HTTP de forma limpa."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()