"""
runner.py

Synchronous/threaded entrypoint for kalshi_orderbook.

This module allows running the async orderbook feed in a background
daemon thread so synchronous code can safely query OrderbookManager.

Design:
- One event loop per thread
- Async feed remains untouched
- Thread exits with process
"""

import asyncio
import threading
import logging
from typing import Iterable

from .orderbook_manager import OrderbookManager
from .ws_feed import OrderbookFeed

logger = logging.getLogger(__name__)


def run_feed_thread(
    manager: OrderbookManager,
    ws_client,
    market_tickers: Iterable[str],
):
    """
    Internal target function for background thread.
    """

    async def _main():
        feed = OrderbookFeed(manager, ws_client)
        ws_client.on_message = feed.on_message
        ws_client.on_open = lambda: feed.on_open(market_tickers)

        await feed.start()
        await ws_client.connect()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_main())
    finally:
        loop.close()


def start_background_feed(
    manager: OrderbookManager,
    ws_client,
    market_tickers: Iterable[str],
    *,
    daemon: bool = True,
) -> threading.Thread:
    """
    Start the orderbook feed in a background thread.

    Args:
        manager: OrderbookManager instance (shared with main thread)
        ws_client: Initialized Kalshi WebSocket client
        market_tickers: Iterable of market tickers
        daemon: Whether thread is daemonized

    Returns:
        threading.Thread
    """

    thread = threading.Thread(
        target=run_feed_thread,
        args=(manager, ws_client, market_tickers),
        daemon=daemon,
        name="kalshi-orderbook-feed",
    )
    thread.start()

    logger.info("Orderbook feed thread started")
    return thread
