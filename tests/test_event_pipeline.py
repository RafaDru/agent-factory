import pytest
from unittest.mock import Mock, patch, MagicMock
from src.protocols.events import EventNotifier
from src.dashboard.handler import DashboardHandler
from src.registry import Registry

@pytest.fixture
def temp_project_dir(tmp_path):
    project = tmp_path / "test_project"
    project.mkdir()
    return project

@pytest.fixture
def notifier(temp_project_dir):
    return EventNotifier(project_name="test_project", base_path=temp_project_dir)

def test_emit_persists_event(notifier, temp_project_dir):
    event = {"type": "mission_start", "data": {"mission_id": "123"}}
    notifier.emit(event)
    events_file = temp_project_dir / ".agent-events" / "test_project" / "events.jsonl"
    assert events_file.exists()
    with open(events_file) as f:
        lines = f.readlines()
    assert len(lines) == 1
    import json
    persisted = json.loads(lines[0])
    assert persisted["type"] == "mission_start"
    assert persisted["data"]["mission_id"] == "123"

def test_get_events_returns_persisted(notifier):
    notifier.emit({"type": "a"})
    notifier.emit({"type": "b"})
    events = notifier.get_events()
    assert len(events) == 2
    assert events[0]["type"] == "a"
    assert events[1]["type"] == "b"

def test_notify_sse_clients_sends_to_registered(notifier):
    client1 = Mock()
    client2 = Mock()
    notifier.register_sse_client(client1)
    notifier.register_sse_client(client2)
    event = {"type": "test"}
    notifier._notify_sse_clients(event)
    client1.send.assert_called_once_with(event)
    client2.send.assert_called_once_with(event)

def test_dashboard_handler_serve_events_returns_json():
    handler = DashboardHandler()
    handler.notifier = MagicMock()
    handler.notifier.get_events.return_value = [{"type": "ev1"}]
    response = handler._serve_events()
    assert response["status"] == 200
    assert response["body"] == [{"type": "ev1"}]

def test_registry_get_notifier_returns_same_instance():
    registry = Registry()
    notifier1 = registry.get_notifier("proj1")
    notifier2 = registry.get_notifier("proj1")
    assert notifier1 is notifier2

def test_dashboard_server_initializes_notifiers_from_registry():
    registry = Registry()
    registry.get_notifier = MagicMock(return_value=Mock())
    from src.dashboard.server import DashboardServer
    server = DashboardServer(registry=registry)
    server._init_notifiers()
    registry.get_notifier.assert_called()