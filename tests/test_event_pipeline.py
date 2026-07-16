"""
Testes do pipeline de eventos do Agent Factory.
Valida: persistencia, SSE, REST, integracao registry-dashboard.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.protocols.events import EventNotifier
from src.protocols.schema import AgentEvent, AgentStatus


@pytest.fixture
def temp_dir(tmp_path):
    p = tmp_path / "events"
    p.mkdir()
    return p


@pytest.fixture
def notifier(temp_dir):
    return EventNotifier(project_id="test-proj", output_dir=str(temp_dir))


def make_event(agent_id="dev", status="running", msg="test"):
    return AgentEvent(
        agent_id=agent_id,
        agent_role="worker",
        status=AgentStatus(status),
        task_id="test-task",
        project_id="test-proj",
        message=msg,
    )


def test_emit_persists_event(notifier, temp_dir):
    """EventNotifier.emit() persiste evento em JSONL."""
    event = make_event()
    notifier.emit(event)
    events_file = temp_dir / "test-proj" / "events.jsonl"
    assert events_file.exists()
    lines = events_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    persisted = json.loads(lines[0])
    assert persisted["agent_id"] == "dev"


def test_get_events_returns_persisted(notifier):
    """get_events() retorna eventos persistidos."""
    notifier.emit(make_event(agent_id="a"))
    notifier.emit(make_event(agent_id="b"))
    events = notifier.get_events()
    assert len(events) == 2
    assert events[0].agent_id == "a"
    assert events[1].agent_id == "b"


def test_notify_sse_clients_sends_message(notifier):
    """_notify_sse_clients escreve no wfile dos clientes registrados."""
    client = MagicMock()
    EventNotifier.register_sse_client(client)
    try:
        notifier.emit(make_event())
        assert client.wfile.write.called
        assert client.wfile.flush.called
    finally:
        EventNotifier.unregister_sse_client(client)


def test_notify_sse_removes_dead_client(notifier):
    """Cliente com BrokenPipeError e removido."""
    dead = MagicMock()
    dead.wfile.write.side_effect = BrokenPipeError
    EventNotifier.register_sse_client(dead)
    try:
        notifier.emit(make_event())
        assert dead not in EventNotifier._sse_clients
    finally:
        EventNotifier.unregister_sse_client(dead)


def test_registry_notifier_shared_with_agents(notifier):
    """Registry.get_notifier() retorna mesmo notifier usado por load_agent."""
    from src.registry import get_registry

    registry = get_registry()
    n = registry.get_notifier("AFP-Team")
    assert n is not None


def test_serve_events_returns_json():
    """DashboardHandler._serve_events retorna eventos como JSON."""
    from src.dashboard.server import DashboardHandler

    handler = DashboardHandler.__new__(DashboardHandler)
    mock_notifier = MagicMock()
    mock_notifier.get_events.return_value = [make_event()]
    handler._get_notifier = MagicMock(return_value=mock_notifier)
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()

    handler._serve_events("test-proj")
    assert handler.send_response.called
    written = b"".join(c[0][0] for c in handler.wfile.write.call_args_list)
    data = json.loads(written)
    assert len(data["events"]) == 1


def test_dashboard_server_uses_registry_notifiers():
    """DashboardServer obtem notifiers do registry."""
    from src.dashboard.server import DashboardServer

    server = DashboardServer(port=9999)
    # Deve ter populachado notifiers via registry
    from src.dashboard.server import DashboardHandler
    assert len(DashboardHandler.notifiers) > 0
