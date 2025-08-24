"""
Background News Scheduler
Periodically fetches and updates financial news in the database.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import threading
from backend.utils.news import get_aggregated_financial_news

logger = logging.getLogger(__name__)

class NewsScheduler:
    """Manages periodic news fetching and database updates"""
    
    def __init__(self, fetch_interval_minutes: int = 45):
        """
        Initialize news scheduler
        
        Args:
            fetch_interval_minutes: How often to fetch news (default: 45 minutes)
        """
        self.fetch_interval_minutes = fetch_interval_minutes
        self.is_running = False
        self.scheduler_task = None
        self.last_fetch_time = None
        
    async def start_scheduler(self):
        """Start the periodic news fetching scheduler"""
        if self.is_running:
            logger.warning("📰 News scheduler is already running")
            return
            
        self.is_running = True
        logger.info(f"🚀 Starting news scheduler (fetch every {self.fetch_interval_minutes} minutes)")
        
        # Run initial fetch immediately
        await self.fetch_news_update()
        
        # Schedule periodic fetching
        while self.is_running:
            try:
                await asyncio.sleep(self.fetch_interval_minutes * 60)  # Convert to seconds
                
                if self.is_running:  # Check if still running after sleep
                    await self.fetch_news_update()
            except Exception as e:
                logger.error(f"❌ Error in news scheduler: {e}")
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    def stop_scheduler(self):
        """Stop the news scheduler"""
        logger.info("🛑 Stopping news scheduler")
        self.is_running = False
        
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            
    async def fetch_news_update(self):
        """Fetch news and update database"""
        try:
            start_time = datetime.now()
            logger.info("🔄 Starting scheduled news fetch...")
            
            # Force refresh to get latest articles and update database
            await get_aggregated_financial_news(force_refresh=True)
            
            self.last_fetch_time = datetime.now()
            elapsed_time = (self.last_fetch_time - start_time).total_seconds()
            
            logger.info(f"✅ Scheduled news fetch completed in {elapsed_time:.1f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Scheduled news fetch failed: {e}")
            
    def get_status(self) -> dict:
        """Get scheduler status information"""
        return {
            "is_running": self.is_running,
            "fetch_interval_minutes": self.fetch_interval_minutes,
            "last_fetch_time": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            "next_fetch_in_minutes": self.get_time_until_next_fetch()
        }
        
    def get_time_until_next_fetch(self) -> Optional[int]:
        """Get minutes until next scheduled fetch"""
        if not self.last_fetch_time or not self.is_running:
            return None
            
        next_fetch_time = self.last_fetch_time + timedelta(minutes=self.fetch_interval_minutes)
        time_until = next_fetch_time - datetime.now()
        
        if time_until.total_seconds() <= 0:
            return 0
            
        return int(time_until.total_seconds() / 60)

# Global scheduler instance
_news_scheduler: Optional[NewsScheduler] = None

def get_news_scheduler() -> NewsScheduler:
    """Get or create global news scheduler instance"""
    global _news_scheduler
    if _news_scheduler is None:
        _news_scheduler = NewsScheduler()
    return _news_scheduler

def start_background_scheduler():
    """Start the news scheduler in the background"""
    scheduler = get_news_scheduler()
    
    def run_scheduler():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scheduler.start_scheduler())
        except Exception as e:
            logger.error(f"Background scheduler error: {e}")
        finally:
            loop.close()
    
    if not scheduler.is_running:
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        logger.info("📰 Background news scheduler thread started")
    else:
        logger.info("📰 Background news scheduler already running")

def stop_background_scheduler():
    """Stop the background news scheduler"""
    scheduler = get_news_scheduler()
    scheduler.stop_scheduler()
