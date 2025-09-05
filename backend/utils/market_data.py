"""
Marketstack EOD fetcher and SQLite storage.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import httpx

from backend.shared.logger import get_logger
from backend.shared.constants import MARKETSTACK_EOD_URL, MARKET_DATA_DB_PATH


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

    async def fetch_marketstack_eod(self, url: str = MARKETSTACK_EOD_URL, symbols: str = "TUPRS.IS", limit: int = 10) -> Dict[str, Any]:
        logger.info(f"Fetching Marketstack EOD: {url}")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params={"symbols": symbols, "limit": limit})
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

    def get_latest_quotes(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT raw_json FROM eod_quotes WHERE symbol=? ORDER BY date DESC LIMIT ?",
                (symbol, limit),
            )
            rows = cur.fetchall()
        return [json.loads(r[0]) for r in rows]


store = MarketDataStore()


async def refresh_eod() -> int:
    payload = await store.fetch_marketstack_eod()
    return store.upsert_eod_batch(payload)


