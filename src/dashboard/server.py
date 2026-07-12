"""
Agent Factory — Dashboard Server
==================================
Server HTTP simples para dashboard.
Eventos são servidos via API REST, frontend faz polling.
"""

import json
from pathlib import Path
from typing import Optional, Any
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

from ..protocols.events import EventNotifier


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer com suporte a múltiplas threads."""
    daemon_threads = True


class DashboardHandler(SimpleHTTPRequestHandler):
    """Handler HTTP para o dashboard."""
    
    notifiers: dict[str, EventNotifier] = {}
    context_stores: dict[str, Any] = {}
    agent_providers: dict[str, str] = {}  # agent_id → "local_multi" | "cloud" | "auto"
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        project_id = params.get("project", [None])[0]
        
        if path == "/" or path == "/index.html":
            self._serve_dashboard()
        elif path == "/api/events":
            self._serve_events(project_id)
        elif path == "/api/status":
            self._serve_status(project_id)
        elif path == "/api/context":
            self._serve_context(project_id)
        elif path == "/api/projects":
            self._serve_projects()
        elif path.startswith("/api/agent/") and path.endswith("/provider"):
            self._serve_agent_provider(path)
        elif path == "/api/debug":
            self._serve_debug()
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith("/api/agent/") and path.endswith("/provider"):
            self._post_agent_provider(path)
        else:
            self.send_error(404)
    
    def _serve_agent_provider(self, path: str):
        """GET: retorna o provider configurado para um agente."""
        import re
        m = re.match(r"/api/agent/(.+)/provider", path)
        if not m:
            self.send_error(400)
            return
        agent_id = m.group(1)
        provider = self.agent_providers.get(agent_id, "auto")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"agent_id": agent_id, "provider": provider}).encode("utf-8"))
    
    def _post_agent_provider(self, path: str):
        """POST: atualiza o provider de um agente."""
        import re
        m = re.match(r"/api/agent/(.+)/provider", path)
        if not m:
            self.send_error(400)
            return
        agent_id = m.group(1)
        
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            self.send_error(400, "Body required")
            return
        
        body = json.loads(self.rfile.read(content_len))
        provider = body.get("provider", "auto")
        valid = ("auto", "local_multi", "cloud")
        if provider not in valid:
            self.send_error(400, f"Provider inválido. Opções: {valid}")
            return
        
        self.agent_providers[agent_id] = provider
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "agent_id": agent_id,
            "provider": provider,
            "previous": self.agent_providers.get(agent_id, "auto"),
        }).encode("utf-8"))
    
    def _serve_dashboard(self):
        """Serve o HTML do dashboard."""
        dashboard_path = Path(__file__).parent / "index.html"
        if dashboard_path.exists():
            with open(dashboard_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_error(404, "Dashboard not found")
    
    def _get_notifier(self, project_id: Optional[str] = None) -> Optional[EventNotifier]:
        if project_id and project_id in self.notifiers:
            return self.notifiers[project_id]
        if len(self.notifiers) == 1:
            return list(self.notifiers.values())[0]
        if project_id is None and len(self.notifiers) > 0:
            return list(self.notifiers.values())[0]
        return None
    
    def _get_context_store(self, project_id: Optional[str] = None) -> Optional[Any]:
        if project_id and project_id in self.context_stores:
            return self.context_stores[project_id]
        if len(self.context_stores) == 1:
            return list(self.context_stores.values())[0]
        if project_id is None and len(self.context_stores) > 0:
            return list(self.context_stores.values())[0]
        return None
    
    def _serve_events(self, project_id: Optional[str] = None):
        """Serve eventos em JSON, incluindo provider config por agente."""
        if project_id:
            notifier = self._get_notifier(project_id)
            notifiers = [notifier] if notifier else []
        else:
            notifiers = list(self.notifiers.values())
        
        all_events = []
        for n in notifiers:
            try:
                evts = n.get_events()
                all_events.extend(evts)
            except Exception as e:
                print(f"[Dashboard] Erro ao ler eventos de {n.project_id}: {e}")
        
        print(f"[Dashboard] _serve_events project={project_id} notifiers={list(self.notifiers.keys())} events_per_notifier={[len(n.get_events()) for n in self.notifiers.values()]} total={len(all_events)}")
        
        all_events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Extrair modelo do ultimo evento "llm-model" de cada agente
        agent_models: dict[str, str] = {}
        for e in reversed(all_events):
            aid = e.agent_id
            if aid not in agent_models:
                m = e.metrics.get("model") if e.metrics else None
                if m:
                    agent_models[aid] = m
                elif e.payload and isinstance(e.payload, dict):
                    m = e.payload.get("model") or e.payload.get("provider_model")
                    if m:
                        agent_models[aid] = m
        
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
    
    def _serve_status(self, project_id: Optional[str] = None):
        """Serve status atual em JSON."""
        notifier = self._get_notifier(project_id)
        if notifier:
            data = notifier.get_status()
        else:
            data = {"project_id": project_id, "phase": "unknown", "progress": 0}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def _serve_context(self, project_id: Optional[str] = None):
        """Serve métricas reais de contexto do ContextStore + event metrics."""
        store = self._get_context_store(project_id)
        notifier = self._get_notifier(project_id)
        data = {"agents": {}, "project": project_id or "unknown"}
        
        def _get_entry(agent_id):
            entry = {}
            if store:
                try:
                    agent_events_store = store.get_agent_history(agent_id, limit=10000)
                    context_data = store.get_agent_context(agent_id)
                    entry = {
                        "events": len(agent_events_store),
                        "context_size_bytes": len(json.dumps(context_data)) if context_data else 0,
                        "has_context": bool(context_data),
                        "last_event": agent_events_store[0]["timestamp"] if agent_events_store else None,
                    }
                except Exception:
                    pass
            if notifier:
                for event in reversed(notifier.get_events()):
                    if event.agent_id == agent_id and event.metrics.get("context"):
                        entry["context_tracking"] = event.metrics["context"]
                        break
            return entry
        
        agent_ids = self._list_agent_ids(project_id)
        if not agent_ids and store:
            try:
                stats = store.get_stats()
                data["project_stats"] = stats
            except Exception:
                pass
        
        for agent_id in agent_ids:
            data["agents"][agent_id] = _get_entry(agent_id)
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
    
    def _list_agent_ids(self, project_id: Optional[str] = None) -> list[str]:
        """Lista IDs de agentes de um projeto via notifier."""
        notifier = self._get_notifier(project_id)
        if not notifier:
            return []
        seen = set()
        for event in notifier.get_events():
            seen.add(event.agent_id)
        return sorted(seen)
    
    def _serve_projects(self):
        """Lista todos os projetos registrados."""
        data = list(self.notifiers.keys())
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        """Suprimir logs padrao."""
        pass

    def _serve_debug(self):
        """Debug: retorna info dos notifiers."""
        info = {}
        for key, n in self.notifiers.items():
            try:
                evts = n.get_events()
                info[key] = {"event_count": len(evts), "file": str(n._events_file), "file_exists": n._events_file.exists()}
            except Exception as e:
                info[key] = {"error": str(e), "file": str(n._events_file)}
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
    Server do dashboard.
    
    Uso:
        notifier = EventNotifier("my-project")
        server = DashboardServer(notifier, port=8080)
        server.start()
    """
    
    def __init__(
        self,
        notifier: EventNotifier,
        port: int = 8080,
        host: str = "localhost",
        context_store: Optional[Any] = None,
    ):
        self.notifier = notifier
        self.port = port
        self.host = host
        self._server: Optional[HTTPServer] = None
        
        DashboardHandler.notifiers[notifier.project_id] = notifier
        if context_store:
            DashboardHandler.context_stores[notifier.project_id] = context_store
    
    def add_notifier(self, notifier: EventNotifier):
        DashboardHandler.notifiers[notifier.project_id] = notifier
    
    def add_context_store(self, project_id: str, context_store: Any):
        DashboardHandler.context_stores[project_id] = context_store
    
    def start(self):
        """Inicia o server."""
        self._server = ThreadingHTTPServer((self.host, self.port), DashboardHandler)
        
        print(f"Dashboard: http://{self.host}:{self.port}")
        print(f"Projetos: {list(DashboardHandler.notifiers.keys())}")
        if DashboardHandler.context_stores:
            print(f"ContextStores ativos: {list(DashboardHandler.context_stores.keys())}")
        
        self._server.serve_forever()
    
    def stop(self):
        """Para o server."""
        if self._server:
            self._server.shutdown()
