"""
Daily scheduler for Marketstack EOD.
"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta

from backend.utils.market_data import refresh_eod


logger = logging.getLogger(__name__)


class MarketScheduler:
    def __init__(self, interval_hours: int = 24):
        self.interval_hours = interval_hours
        self.is_running = False

    async def _run_loop(self):
        if self.is_running:
            logger.info("Market EOD scheduler already running")
            return
        self.is_running = True
        # Initial run
        await self._tick()
        while self.is_running:
            try:
                await asyncio.sleep(self.interval_hours * 3600)
                if self.is_running:
                    await self._tick()
            except Exception as e:
                logger.error(f"Market scheduler loop error: {e}")
                await asyncio.sleep(60)

    async def _tick(self):
        logger.info("Running scheduled Marketstack EOD refresh...")
        try:
            saved = await refresh_eod()
            logger.info(f"Marketstack EOD refresh complete. Saved {saved} rows.")
        except Exception as e:
            logger.error(f"Marketstack EOD refresh failed: {e}")

    def start_background(self):
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_loop())
            finally:
                loop.close()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        logger.info("Market EOD scheduler thread started")


_market_scheduler = MarketScheduler()


def start_market_scheduler():
    _market_scheduler.start_background()

def stop_market_scheduler():
    _market_scheduler.is_running = False


