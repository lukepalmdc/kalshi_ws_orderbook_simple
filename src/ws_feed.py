"""
feed.py

Async WebSocket ingestion layer for Kalshi orderbook data.

Responsibilities:
- Receive raw websocket messages
- Buffer messages via asyncio.Queue
- Dispatch snapshots and deltas into OrderbookManager
- Maintain strict snapshot-before-delta correctness

This module owns ALL asyncio constructs.
"""

import asyncio
import json
import logging
from typing import Iterable, Optional

from .orderbook_manager import OrderbookManager

logger = logging.getLogger(__name__)


class OrderbookFeed:
    """
    Async orderbook feed processor.

    Design:
    - Single async consumer (writer)
    - OrderbookManager handles locking for readers
    - No message dropping unless queue is full
    """

    def __init__(
        self,
        manager: OrderbookManager,
        ws_client,
        *,
        queue_size: int = 10_000,
    ):
        self.manager = manager
        self.ws_client = ws_client
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)

        self._consumer_task: Optional[asyncio.Task] = None
        self._running = False

    # ---------------------------
    # WebSocket callbacks
    # ---------------------------

    async def on_message(self, message):
        """
        WebSocket message handler.

        This should be wired directly to ws_client.on_message.
        """
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                logger.warning("Failed to decode websocket message")
                self.manager.dropped_messages += 1
                return

        try:
            self.queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.error("Orderbook queue full — backpressure detected")
            self.manager.dropped_messages += 1

    async def on_open(self, market_tickers: Iterable[str]):
        """
        Called once websocket connection is established.
        """
        await self.ws_client.subscribe_to_markets(
            channels=["orderbook_delta"],
            market_tickers=list(market_tickers),
        )
        logger.info("Subscribed to %d markets", len(list(market_tickers)))

    # ---------------------------
    # Consumer loop
    # ---------------------------

    async def _consume(self):
        """
        Internal message processing loop.

        Invariant:
        - Exactly one task mutates OrderbookManager
        """
        self._running = True

        while self._running:
            try:
                message = await self.queue.get()
                msg_type = message.get("type")

                if msg_type == "orderbook_snapshot":
                    self.manager.handle_snapshot(message["msg"])

                elif msg_type == "orderbook_delta":
                    self.manager.handle_delta(message["msg"])

                elif msg_type == "subscribed":
                    logger.info("WebSocket subscription confirmed")

                elif msg_type == "error":
                    logger.error("WebSocket error: %s", message)

                else:
                    logger.debug("Unhandled message type: %s", msg_type)

                self.queue.task_done()

            except Exception:
                logger.exception("Error processing orderbook message")

    # ---------------------------
    # Lifecycle control
    # ---------------------------

    async def start(self):
        """
        Start the consumer task.

        Must be called after event loop is running.
        """
        if self._consumer_task is not None:
            return

        self._consumer_task = asyncio.create_task(self._consume())
        logger.info("Orderbook feed consumer started")

    async def stop(self):
        """
        Stop processing messages gracefully.
        """
        self._running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

            self._consumer_task = None
            logger.info("Orderbook feed consumer stopped")