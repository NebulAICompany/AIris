"""
Marketstack EOD fetcher and SQLite storage.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx

from backend.shared.logger import get_logger
from backend.shared.constants import MARKETSTACK_EOD_URL, MARKET_DATA_DB_PATH, MARKETSTACK_EOD_API_KEY


logger = get_logger("MARKET_DATA")


class MarketDataStore:
    def __init__(self, db_path: Path = MARKET_DATA_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        logger.info(f"Initializing database: {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS eod_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    raw_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_eod_symbol_date ON eod_quotes(symbol, date DESC)"
            )
            conn.commit()

    async def fetch_marketstack_eod(self, url: str = MARKETSTACK_EOD_URL, symbols: str = "TUPRS.IS", limit: int = 30) -> Dict[str, Any]:
        logger.info(f"Fetching Marketstack EOD: {url}")
        symbol_count = len(symbols.split(","))
        # Calculate date_from as today - limit days in yyyy-mm-dd format
        date_from = (datetime.now() - timedelta(days=limit)).date().isoformat()
        logger.info(f"Fetching data from date: {date_from}")
        
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params={
                "access_key": MARKETSTACK_EOD_API_KEY, 
                "symbols": symbols, 
                "date_from": date_from,
                "limit": limit*symbol_count
            })
            r.raise_for_status()
            return r.json()

    def upsert_eod_batch(self, payload: Dict[str, Any]) -> int:
        data: List[Dict[str, Any]] = payload.get("data", [])
        saved = 0
        with sqlite3.connect(self.db_path) as conn:
            for item in data:
                try:
                    symbol = item.get("symbol")
                    date_str = item.get("date")
                    # Normalize date to YYYY-MM-DD
                    date_norm = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date().isoformat()
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO eod_quotes(
                            symbol, date, open, high, low, close, volume, raw_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            symbol,
                            date_norm,
                            item.get("open"),
                            item.get("high"),
                            item.get("low"),
                            item.get("close"),
                            item.get("volume"),
                            json.dumps(item, ensure_ascii=False),
                        ),
                    )
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to upsert EOD row: {e}")
            conn.commit()
        logger.info(f"Saved {saved} EOD rows")
        logger.info(f"Saved EOD rows: {data}")
        return saved

    def get_most_changed_quotes(self, symbols: List[str], limit: int = 30, chart_num: int = 8) -> List[Dict[str, Any]]:
        """
        Get the most changed quotes by absolute percentage over a given period.
        
        Args:
            symbols: List of stock symbols to analyze
            limit: Number of days to look back from today (default: 30)
            chart_num: Number of top movers to return (default: 8)
            
        Returns:
            List of dictionaries containing symbol and all data for the period,
            ordered by absolute percentage change (descending). Includes both
            positive and negative changes, with the largest absolute changes first.
        """
        # Calculate the date that is 'limit' days ago from today
        cutoff_date = (datetime.now() - timedelta(days=limit)).date().isoformat()
        
        results = []
        with sqlite3.connect(self.db_path) as conn:
            for symbol in symbols:
                # Get all data for this symbol within the last 'limit' days
                cur = conn.execute(
                    """
                    SELECT raw_json FROM eod_quotes 
                    WHERE symbol = ? AND date >= ?
                    ORDER BY date DESC
                    """,
                    (symbol, cutoff_date)
                )
                rows = cur.fetchall()
                
                if len(rows) < 2:  # Need at least 2 data points to calculate change
                    continue
                    
                # Parse the data
                data = [json.loads(r[0]) for r in rows]
                
                # Calculate percentage change from first (oldest) to last (newest) day
                first_close = data[-1]['close']  # Last in array is oldest
                last_close = data[0]['close']    # First in array is newest
                if first_close is None or last_close is None or first_close == 0:
                    continue
                    
                change_percent = ((last_close - first_close) / first_close) * 100
                
                results.append({
                    'symbol': symbol,
                    'change_percent': change_percent,
                    'absolute_change_percent': abs(change_percent),
                    'data': data
                })
        
        # Sort by absolute percentage change (descending) and return top chart_num
        results.sort(key=lambda x: x['absolute_change_percent'], reverse=True)
        logger.info(f"Most changed quotes: {[x['symbol'] for x in results]} with change_percent: {[round(x['change_percent'], 3) for x in results]}")
        return results[:chart_num]

    def get_latest_quotes(self, symbol: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Get quotes for a symbol from the last N days.
        
        Args:
            symbol: Stock symbol to get quotes for
            limit: Number of days to look back from today (default: 30)
            
        Returns:
            List of quote data from the last N days, ordered by date (newest first)
        """
        # Calculate the date that is 'limit' days ago from today
        cutoff_date = (datetime.now() - timedelta(days=limit)).date().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT raw_json FROM eod_quotes WHERE symbol=? AND date >= ? ORDER BY date DESC",
                (symbol, cutoff_date),
            )
            rows = cur.fetchall()
        return [json.loads(r[0]) for r in rows]


store = MarketDataStore()


async def refresh_eod(symbols: str = "TUPRS.IS", limit: int = 7) -> int:
    payload = await store.fetch_marketstack_eod(symbols=symbols, limit=limit)
    return store.upsert_eod_batch(payload)


