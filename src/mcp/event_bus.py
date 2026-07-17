"""MCP Gateway — Event Bus Integration"""
import logging
from typing import Any, Optional

from src.eventbus.amqp import AMQPConnection, RPCClient, DEFAULT_URL

logger = logging.getLogger(__name__)

_CONN: Optional[AMQPConnection] = None


def _ensure_conn() -> Optional[AMQPConnection]:
    global _CONN
    if _CONN is None or not _CONN.is_connected:
        _CONN = AMQPConnection(DEFAULT_URL)
        try:
            _CONN.connect()
            logger.info("Event Bus conectado para MCP Gateway")
        except Exception as e:
            logger.warning("Event Bus indisponivel: %s. Usando modo in-process.", e)
            _CONN = None
    return _CONN


def call_agent_via_event_bus(
    agent_id: str,
    task: dict[str, Any],
    timeout: float = 60.0,
) -> Optional[dict]:
    """Publica task no RabbitMQ e aguarda resposta do runtime."""
    conn = _ensure_conn()
    if conn is None:
        return None

    client = RPCClient(conn, timeout=timeout)
    routing_key = f"task.run.{agent_id}"
    result = client.call(routing_key, task)

    if result is None:
        logger.warning("Timeout chamando %s via Event Bus", agent_id)
    return result


def event_bus_available() -> bool:
    conn = _ensure_conn()
    return conn is not None
