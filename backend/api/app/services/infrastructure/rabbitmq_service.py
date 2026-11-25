# backend/api/app/services/rabbitmq_service.py
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Final, Optional

import aio_pika
import aio_pika.abc
from aiormq.exceptions import AMQPError
from fastapi import Depends

from app.core.config import CoreSettings, get_core_settings

logger = logging.getLogger("airdeliver.rabbitmq")

EXCHANGE_NAME: Final[str] = "airdeliver_main_exchange"
EXCHANGE_TYPE: Final[aio_pika.ExchangeType] = aio_pika.ExchangeType.TOPIC
DLX_NAME: Final[str] = "airdeliver_dlx"
DLQ_NAME: Final[str] = "airdeliver_dlq"
APP_ID: Final[str] = "airdeliver-api"

CHANNEL_PREFETCH: Final[int] = 64
PUBLISH_TIMEOUT_SEC: Final[float] = 5.0
CONNECT_HANDSHAKE_TIMEOUT_SEC: Final[float] = 30.0
HEARTBEAT_SEC: Final[int] = 60
MAX_CONNECT_RETRIES: Final[int] = 10
CONNECT_BASE_DELAY_SEC: Final[float] = 1.5
CONNECT_MAX_DELAY_SEC: Final[float] = 12.0
PUBLISH_MAX_RETRIES: Final[int] = 3
PUBLISH_RETRY_BASE_SEC: Final[float] = 0.3


class PublishResult(Enum):
    CONFIRMED = "confirmed"
    NACKED = "nacked"
    EXHAUSTED = "exhausted"
    SERIALIZATION_ERROR = "serialization_error"


@dataclass(frozen=True, slots=True)
class PublishOutcome:
    result: PublishResult
    routing_key: str
    correlation_id: str
    attempts: int
    elapsed_ms: float
    error_detail: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.result == PublishResult.CONFIRMED


@dataclass(slots=True)
class _BrokerTopology:
    connection: aio_pika.abc.AbstractRobustConnection
    channel: aio_pika.abc.AbstractChannel
    exchange: aio_pika.abc.AbstractExchange
    dlx: aio_pika.abc.AbstractExchange


class RabbitMQService:
    """
    Production-grade RabbitMQ service for FastAPI + aio_pika.

    Characteristics:
    - Async-safe, idempotent connect path.
    - Robust connection with reconnect-aware topology rehydration.
    - Publisher confirms enabled.
    - Dead-letter exchange and queue provisioned automatically.
    - Structured logging without leaking payloads or credentials.
    - Typed publish results; no silent message loss contract.
    """

    def __init__(self, settings: CoreSettings) -> None:
        self._settings = settings
        self._topology: Optional[_BrokerTopology] = None
        self._connect_lock = asyncio.Lock()

    async def connect(self) -> None:
        """
        Establish a healthy broker topology if one does not already exist.

        Safe to call concurrently from multiple coroutines.
        """
        async with self._connect_lock:
            if self._topology is not None and not self._topology.connection.is_closed:
                return

            last_exc: Exception = RuntimeError("RabbitMQ connect not attempted")

            for attempt in range(1, MAX_CONNECT_RETRIES + 1):
                try:
                    logger.info(
                        "rabbitmq.connect.attempt",
                        extra={
                            "host": self._settings.RABBITMQ_HOST,
                            "attempt": attempt,
                            "max_attempts": MAX_CONNECT_RETRIES,
                        },
                    )

                    topology = await self._build_topology()
                    self._topology = topology

                    logger.info(
                        "rabbitmq.connect.success",
                        extra={
                            "exchange": EXCHANGE_NAME,
                            "dlx": DLX_NAME,
                            "dlq": DLQ_NAME,
                        },
                    )
                    return

                except (OSError, AMQPError, asyncio.TimeoutError, ConnectionRefusedError) as exc:
                    last_exc = exc

                    if attempt == MAX_CONNECT_RETRIES:
                        break

                    delay = min(
                        CONNECT_BASE_DELAY_SEC * (1.5 ** (attempt - 1)),
                        CONNECT_MAX_DELAY_SEC,
                    )
                    logger.warning('rabbitmq.connect.retry', extra={'attempt': attempt, 'retry_in_sec': round(delay, 2)})
                    await asyncio.sleep(delay)

            logger.critical('rabbitmq.connect.failed', extra={'attempts': MAX_CONNECT_RETRIES})
            raise last_exc

    async def close(self) -> None:
        """
        Gracefully release AMQP resources in dependency order.
        """
        topology = self._topology
        self._topology = None

        if topology is None:
            return

        try:
            if not topology.channel.is_closed:
                await topology.channel.close()
        except Exception as exc:
            logger.warning('rabbitmq.close.channel_error', extra={})

        try:
            if not topology.connection.is_closed:
                await topology.connection.close()
            logger.info("rabbitmq.close.success")
        except Exception as exc:
            logger.error('rabbitmq.close.connection_error', extra={})

    async def publish(
        self,
        body: dict[str, Any],
        routing_key: str,
        correlation_id: Optional[str] = None,
        max_retries: int = PUBLISH_MAX_RETRIES,
        message_id: Optional[str] = None,
    ) -> PublishOutcome:
        """
        Publish a JSON message with publisher confirms.

        Returns a typed PublishOutcome. Callers can decide whether to raise
        an HTTP 503, enqueue fallback work, or emit alerts.
        """
        cid = correlation_id or str(uuid.uuid4())
        mid = message_id or str(uuid.uuid4())
        started_at = time.monotonic()

        try:
            payload = json.dumps(body, default=str).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.error('rabbitmq.publish.serialization_error', extra={'routing_key': routing_key, 'correlation_id': cid})
            return PublishOutcome(
                result=PublishResult.SERIALIZATION_ERROR,
                routing_key=routing_key,
                correlation_id=cid,
                attempts=0,
                elapsed_ms=self._elapsed_ms(started_at),
                error_detail=str(exc),
            )

        last_exc: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                exchange = await self._ensure_exchange()

                message = aio_pika.Message(
                    body=payload,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    app_id=APP_ID,
                    correlation_id=cid,
                    message_id=mid,
                    timestamp=int(time.time()),
                )

                confirmation = await exchange.publish(
                    message,
                    routing_key=routing_key,
                    timeout=PUBLISH_TIMEOUT_SEC,
                )

                elapsed_ms = self._elapsed_ms(started_at)

                if confirmation:
                    logger.debug(
                        "rabbitmq.publish.confirmed",
                        extra={
                            "routing_key": routing_key,
                            "correlation_id": cid,
                            "attempt": attempt,
                            "elapsed_ms": elapsed_ms,
                        },
                    )
                    return PublishOutcome(
                        result=PublishResult.CONFIRMED,
                        routing_key=routing_key,
                        correlation_id=cid,
                        attempts=attempt,
                        elapsed_ms=elapsed_ms,
                    )

                logger.warning(
                    "rabbitmq.publish.nacked",
                    extra={
                        "routing_key": routing_key,
                        "correlation_id": cid,
                        "attempt": attempt,
                    },
                )
                return PublishOutcome(
                    result=PublishResult.NACKED,
                    routing_key=routing_key,
                    correlation_id=cid,
                    attempts=attempt,
                    elapsed_ms=elapsed_ms,
                    error_detail="Broker negative acknowledgement received",
                )

            except (AMQPError, asyncio.TimeoutError, ConnectionError, OSError) as exc:
                last_exc = exc
                logger.warning('rabbitmq.publish.retry', extra={'routing_key': routing_key, 'correlation_id': cid, 'attempt': attempt, 'max_retries': max_retries})
                self._topology = None

                if attempt < max_retries:
                    await asyncio.sleep(PUBLISH_RETRY_BASE_SEC * attempt)

        elapsed_ms = self._elapsed_ms(started_at)
        logger.error('rabbitmq.publish.exhausted', extra={'routing_key': routing_key, 'correlation_id': cid, 'attempts': max_retries, 'elapsed_ms': elapsed_ms})
        return PublishOutcome(
            result=PublishResult.EXHAUSTED,
            routing_key=routing_key,
            correlation_id=cid,
            attempts=max_retries,
            elapsed_ms=elapsed_ms,
            error_detail=str(last_exc) if last_exc else None,
        )

    async def is_healthy(self) -> bool:
        """
        Lightweight readiness/liveness check.
        """
        try:
            topology = self._topology
            return (
                topology is not None
                and not topology.connection.is_closed
                and not topology.channel.is_closed
            )
        except Exception:
            return False

    async def __aenter__(self) -> "RabbitMQService":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _build_topology(self) -> _BrokerTopology:
        connection: aio_pika.abc.AbstractRobustConnection = await aio_pika.connect_robust(
            self._settings.RABBITMQ_URL,
            timeout=CONNECT_HANDSHAKE_TIMEOUT_SEC,
            heartbeat=HEARTBEAT_SEC,
            client_properties={
                "connection_name": f"{APP_ID}-{uuid.uuid4().hex[:8]}"
            },
        )

        channel: aio_pika.abc.AbstractChannel = await connection.channel(
            publisher_confirms=True,
        )
        await channel.set_qos(prefetch_count=CHANNEL_PREFETCH)

        dlx: aio_pika.abc.AbstractExchange = await channel.declare_exchange(
            DLX_NAME,
            type=aio_pika.ExchangeType.FANOUT,
            durable=True,
        )

        dlq = await channel.declare_queue(
            DLQ_NAME,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await dlq.bind(dlx)

        exchange: aio_pika.abc.AbstractExchange = await channel.declare_exchange(
            EXCHANGE_NAME,
            type=EXCHANGE_TYPE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": DLX_NAME,
            },
        )

        return _BrokerTopology(
            connection=connection,
            channel=channel,
            exchange=exchange,
            dlx=dlx,
        )

    async def consume(
        self, queue_name: str, routing_key: str,
        callback: Callable[[aio_pika.abc.AbstractIncomingMessage], Awaitable[Any]],
    ) -> aio_pika.abc.AbstractQueue:
        """Bind a durable consumer using the service's connected topology."""
        exchange = await self._ensure_exchange()
        topology = self._topology
        assert topology is not None, "RabbitMQ topology unavailable after connect()"
        queue = await topology.channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange, routing_key=routing_key)
        await queue.consume(callback)
        return queue

    async def _ensure_exchange(self) -> aio_pika.abc.AbstractExchange:
        topology = self._topology

        if topology is None or topology.connection.is_closed or topology.channel.is_closed:
            await self.connect()
            topology = self._topology

        assert topology is not None, "RabbitMQ topology unavailable after connect()"
        return topology.exchange

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((time.monotonic() - started_at) * 1000, 2)


_instance: Optional[RabbitMQService] = None
_instance_lock = asyncio.Lock()


async def _get_or_create_instance(settings: CoreSettings) -> RabbitMQService:
    global _instance

    if _instance is not None and await _instance.is_healthy():
        return _instance

    async with _instance_lock:
        if _instance is None or not await _instance.is_healthy():
            service = RabbitMQService(settings)
            await service.connect()
            _instance = service

    return _instance


async def get_rabbitmq_service(
    settings: CoreSettings = Depends(get_core_settings),
) -> RabbitMQService:
    """
    FastAPI dependency injection entry point.
    """
    return await _get_or_create_instance(settings)


async def init_rabbitmq() -> None:
    """
    Eager initialization during application startup.
    """
    settings = get_core_settings()
    await _get_or_create_instance(settings)
    logger.info("rabbitmq.lifecycle.initialized")


async def shutdown_rabbitmq() -> None:
    """
    Graceful shutdown hook for application lifespan teardown.
    """
    global _instance

    async with _instance_lock:
        if _instance is not None:
            await _instance.close()
            _instance = None

    logger.info("rabbitmq.lifecycle.shutdown")
