"""
Agent Factory — Agent Runtime
==============================
Loop de consumo RabbitMQ que executa tarefas delegadas via Event Bus.
Cada runtime consome de uma fila especifica (ex: dev-tasks, qa-tasks)
e publica resultados no reply_to indicado.
"""

import json
import logging
import signal
import sys
import threading
import time
from typing import Any, Optional

import pika

from src.eventbus.amqp import AMQPConnection, DEFAULT_URL

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime que consome mensagens do RabbitMQ e executa em um agente.

    Uso:
        runtime = AgentRuntime(agent=dev_agent, queue_name="dev-tasks",
                               routing_keys=["task.run.dev", "agent.ask.dev"])
        runtime.start()  # bloqueante
    """

    def __init__(
        self,
        agent: Any,
        queue_name: str,
        routing_keys: Optional[list[str]] = None,
        amqp_url: str = DEFAULT_URL,
        prefetch_count: int = 1,
    ):
        self.agent = agent
        self.agent_id = agent.agent_id if hasattr(agent, "agent_id") else "unknown"
        self.queue_name = queue_name or f"agent-{self.agent_id}"
        self.routing_keys = routing_keys or [f"task.run.{self.agent_id}", f"agent.ask.{self.agent_id}"]
        self.prefetch_count = prefetch_count
        self._conn = AMQPConnection(amqp_url)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._consuming = False

    def _ensure_channel(self) -> Any:
        ch = self._conn.connect()
        ch.basic_qos(prefetch_count=self.prefetch_count)
        ch.queue_declare(queue=self.queue_name, durable=True)
        for rk in self.routing_keys:
            ch.queue_bind(queue=self.queue_name, exchange="afp", routing_key=rk)
        return ch

    def start(self, block: bool = True):
        self._running = True
        self._consuming = True

        if block:
            self._run_loop()
        else:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("Runtime %s iniciado em background", self.agent_id)

    def _run_loop(self):
        while self._running:
            try:
                ch = self._ensure_channel()
                ch.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._callback,
                    auto_ack=False,
                )
                logger.info("Runtime %s ouvindo %s", self.agent_id, self.queue_name)
                self._consuming = True
                ch.start_consuming()
            except (pika.exceptions.ConnectionWrongStateError,
                    pika.exceptions.AMQPConnectionError,
                    pika.exceptions.StreamLostError,
                    ConnectionResetError,
                    OSError) as e:
                if self._running:
                    logger.warning("Runtime %s perdeu conexao: %s. Reconectando em 3s...", self.agent_id, e)
                    self._conn.reconnect()
                    time.sleep(3)
                    continue
            except Exception as e:
                logger.error("Runtime %s erro fatal: %s", self.agent_id, e)
                if self._running:
                    time.sleep(5)
                    continue
            break

    def _callback(self, ch, method, properties, body):
        try:
            msg = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        action = msg.get("action", "?")
        reply_to = msg.get("reply_to")
        corr_id = msg.get("correlation_id")
        logger.info("[%s] Recebido: %s", self.agent_id, action)

        try:
            result = self.agent.run(msg)
            if hasattr(result, "model_dump"):
                output = result.model_dump(mode="json", exclude_none=True)
            elif isinstance(result, dict):
                output = result
            else:
                output = {"result": str(result)}
        except Exception as e:
            output = {"status": "error", "error": str(e)}

        if reply_to:
            reply_msg = {
                "correlation_id": corr_id,
                "agent_id": self.agent_id,
                "status": "ok" if output.get("status") != "error" else "error",
                "result": output,
            }
            try:
                ch.basic_publish(
                    exchange="afp",
                    routing_key=reply_to,
                    body=json.dumps(reply_msg, ensure_ascii=False, default=str).encode("utf-8"),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type="application/json",
                        correlation_id=corr_id or "",
                    ),
                )
            except Exception as e:
                logger.warning("Falha ao publicar reply: %s", e)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def stop(self, timeout: float = 5.0):
        self._running = False
        self._consuming = False
        if self._conn.is_connected:
            try:
                self._conn.channel.stop_consuming()
            except Exception:
                pass
            self._conn.close()
        logger.info("Runtime %s parado", self.agent_id)


def run_runtime_for(agent_class_path: str, agent_id: str, project_id: str,
                    queue_name: Optional[str] = None, amqp_url: str = DEFAULT_URL):
    """
    Inicia um runtime para um agente especifico, carregando a classe dinamicamente.
    Uso: python -m src.agents.runtime src.agents.factory_dev AgentFactoryDevAgent dev AFP-Team
    """
    import importlib

    module_path, class_name = agent_class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    agent_class = getattr(module, class_name)

    from src.protocols.events import EventNotifier
    notifier = EventNotifier(project_id)
    agent = agent_class(project_id=project_id, notifier=notifier)

    queue = queue_name or f"{agent_id}-tasks"
    runtime = AgentRuntime(
        agent=agent,
        queue_name=queue,
        routing_keys=[f"task.run.{agent_id}", f"agent.ask.{agent_id}"],
        amqp_url=amqp_url,
    )

    def _signal_handler(sig, frame):
        logger.info("Parando runtime %s...", agent_id)
        runtime.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("Iniciando runtime para %s (%s)", agent_id, agent_class.__name__)
    runtime.start(block=True)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if len(sys.argv) >= 4:
        run_runtime_for(sys.argv[1], sys.argv[2], sys.argv[3], 
                        sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        print("Uso: python -m src.agents.runtime <module.class> <agent_id> <project_id> [queue_name]")
        print("Ex:  python -m src.agents.runtime src.agents.factory_dev.AgentFactoryDevAgent dev AFP-Team")
