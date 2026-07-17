"""
Agent Factory — AMQP Event Bus (RabbitMQ)
==========================================
Gerencia conexao RabbitMQ, publisher e consumer base.
Padrao: exchange 'afp' do tipo topic.
"""

import json
import logging
import threading
import time
from typing import Any, Callable, Optional

import pika

logger = logging.getLogger(__name__)

DEFAULT_URL = "amqp://afp:afp123@localhost:5672/"


class AMQPConnection:
    """Gerenciador de conexao RabbitMQ com reconexao automatica."""

    RETRY_DELAY = 3

    def __init__(self, url: str = DEFAULT_URL):
        self.url = url
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.channel.Channel] = None
        self._lock = threading.Lock()

    def connect(self) -> pika.channel.Channel:
        with self._lock:
            if self._connection and self._connection.is_open:
                return self._channel
            try:
                params = pika.URLParameters(self.url)
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                self._channel.exchange_declare(exchange="afp", exchange_type="topic", durable=True)
                logger.info("AMQP conectado a %s", self.url.replace("afp123", "****"))
                return self._channel
            except Exception as e:
                logger.warning("AMQP falhou ao conectar: %s", e)
                self._connection = None
                self._channel = None
                raise

    def reconnect(self):
        self.close()
        time.sleep(self.RETRY_DELAY)
        return self.connect()

    def close(self):
        with self._lock:
            if self._channel and self._channel.is_open:
                self._channel.close()
            if self._connection and self._connection.is_open:
                self._connection.close()
            self._channel = None
            self._connection = None

    @property
    def channel(self) -> Optional[pika.channel.Channel]:
        return self._channel

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_open


class Publisher:
    """Publica mensagens no exchange 'afp'."""

    def __init__(self, connection: AMQPConnection):
        self._conn = connection
        self._ensure_connected()

    def _ensure_connected(self):
        if not self._conn.is_connected:
            self._conn.connect()

    def publish(self, routing_key: str, message: dict) -> bool:
        try:
            self._ensure_connected()
            body = json.dumps(message, ensure_ascii=False, default=str)
            self._conn.channel.basic_publish(
                exchange="afp",
                routing_key=routing_key,
                body=body.encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
            logger.debug("Publicado em %s: %s", routing_key, message.get("action", "?"))
            return True
        except Exception as e:
            logger.warning("Falha ao publicar em %s: %s", routing_key, e)
            return False


class Consumer:
    """Consome mensagens de uma fila no exchange 'afp'."""

    def __init__(
        self,
        connection: AMQPConnection,
        queue_name: str,
        routing_keys: list[str],
        handler: Callable[[dict], Optional[dict]],
        prefetch_count: int = 1,
    ):
        self._conn = connection
        self._queue_name = queue_name
        self._routing_keys = routing_keys
        self._handler = handler
        self._prefetch_count = prefetch_count
        self._tag: Optional[str] = None
        self._running = False

    def start(self):
        ch = self._conn.connect()
        ch.basic_qos(prefetch_count=self._prefetch_count)

        ch.queue_declare(queue=self._queue_name, durable=True)
        for rk in self._routing_keys:
            ch.queue_bind(queue=self._queue_name, exchange="afp", routing_key=rk)

        def callback(ch, method, properties, body):
            try:
                msg = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            try:
                result = self._handler(msg)
                if result is not None:
                    reply_key = msg.get("reply_to")
                    corr_id = msg.get("correlation_id")
                    if reply_key:
                        pub = Publisher(self._conn)
                        pub.publish(reply_key, {
                            "correlation_id": corr_id,
                            "status": "ok",
                            "result": result,
                        })
            except Exception as e:
                logger.error("Handler error on %s: %s", self._queue_name, e)
                reply_key = msg.get("reply_to")
                corr_id = msg.get("correlation_id")
                if reply_key:
                    pub = Publisher(self._conn)
                    pub.publish(reply_key, {
                        "correlation_id": corr_id,
                        "status": "error",
                        "error": str(e),
                    })
            finally:
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self._tag = ch.basic_consume(queue=self._queue_name, on_message_callback=callback)
        self._running = True
        logger.info("Consumer %s ouvindo: %s", self._queue_name, self._routing_keys)

        try:
            ch.start_consuming()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self._running = False
        if self._conn.is_connected and self._tag:
            self._conn.channel.basic_cancel(self._tag)
        logger.info("Consumer %s parado", self._queue_name)


class RPCClient:
    """Cliente RPC: publica e aguarda resposta em fila exclusiva."""

    def __init__(self, connection: AMQPConnection, timeout: float = 30.0):
        self._conn = connection
        self._timeout = timeout
        self._response: Optional[dict] = None
        self._correlation_id: Optional[str] = None
        self._queue: Optional[str] = None
        import uuid
        self._correlation_id = str(uuid.uuid4())

    def call(self, routing_key: str, message: dict) -> Optional[dict]:
        ch = self._conn.connect()
        result = ch.queue_declare(queue="", exclusive=True)
        self._queue = result.method.queue
        reply_rk = f"agent.reply.{self._queue}"

        ch.queue_bind(queue=self._queue, exchange="afp", routing_key=reply_rk)

        self._response = None
        tag = ch.basic_consume(
            queue=self._queue,
            on_message_callback=self._on_response,
            auto_ack=True,
        )

        msg = dict(message)
        msg["correlation_id"] = self._correlation_id
        msg["reply_to"] = reply_rk

        pub = Publisher(self._conn)
        pub.publish(routing_key, msg)

        deadline = time.time() + self._timeout
        while self._response is None and time.time() < deadline:
            try:
                ch.connection.process_data_events(time_limit=0.5)
            except Exception:
                break

        ch.basic_cancel(tag)
        ch.queue_unbind(queue=self._queue, exchange="afp", routing_key=reply_rk)
        return self._response

    def _on_response(self, ch, method, properties, body):
        try:
            msg = json.loads(body.decode("utf-8"))
            if msg.get("correlation_id") == self._correlation_id:
                self._response = msg
        except json.JSONDecodeError:
            pass
