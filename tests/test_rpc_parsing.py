"""Testes de parsing RPC coordinator <-> runtime."""
from src.agents.coordinator import AgentFactoryCoordinator
from src.protocols.schema import OutputStatus


def test_rpc_task_result_success():
    response = {
        "status": "ok",
        "result": {
            "task_id": "t1",
            "agent_id": "dev",
            "project_id": "AFP-Team",
            "status": "completed",
            "output": {"status": "ok", "summary": "Feito", "rationale": "ok"},
            "summary": "COMPLETED: edit_file",
        },
    }
    out = AgentFactoryCoordinator._task_output_from_rpc(response)
    assert out.status == OutputStatus.SUCCESS
    assert out.details.get("summary") == "Feito" or "COMPLETED" in (out.summary or "")


def test_rpc_task_result_failure():
    response = {
        "status": "error",
        "result": {
            "agent_id": "dev",
            "status": "failed",
            "output": {"status": "error", "error": "arquivo nao encontrado"},
            "summary": "FAILED: read_file",
        },
    }
    out = AgentFactoryCoordinator._task_output_from_rpc(response)
    assert out.status == OutputStatus.FAILURE


def test_rpc_empty_body_ok():
    response = {"status": "ok", "result": None}
    out = AgentFactoryCoordinator._task_output_from_rpc(response)
    assert out.status == OutputStatus.SUCCESS


def test_rpc_needs_direction_not_success():
    response = {
        "status": "ok",
        "result": {
            "agent_id": "negocios",
            "status": "completed",
            "output": {
                "status": "needs_direction",
                "rationale": "Acao draft_document nao definida",
                "available_actions": ["write_file"],
            },
            "summary": "COMPLETED: draft_document",
        },
    }
    out = AgentFactoryCoordinator._task_output_from_rpc(response)
    assert out.status == OutputStatus.NEEDS_DIRECTION


def test_rpc_no_response_raises():
    try:
        AgentFactoryCoordinator._task_output_from_rpc(None)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "RPC sem resposta" in str(e)
