"""
Marketstack EOD fetcher and SQLite storage.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import httpx

from backend.shared.logger import get_logger
from backend.shared.constants import MARKETSTACK_EOD_URL, MARKET_DATA_DB_PATH, MARKETSTACK_API_KEY, MARKETSTACK_COMPANY_INFO_URL, MARKETSTACK_TICKERS


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
            
            # Create company_info table if it doesn't exist
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS company_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    name TEXT,
                    exchange TEXT,
                    currency TEXT,
                    country TEXT,
                    sector TEXT,
                    industry TEXT,
                    website TEXT,
                    description TEXT,
                    logo TEXT,
                    fulltime_employees TEXT,
                    raw_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Add fulltime_employees column if it doesn't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE company_info ADD COLUMN fulltime_employees TEXT")
            except sqlite3.OperationalError:
                # Column already exists, ignore
                pass
                
            conn.commit()

    async def fetch_marketstack_eod(self, url: str = MARKETSTACK_EOD_URL, symbols: str = "TUPRS.IS", limit: int = 30) -> Dict[str, Any]:
        logger.info(f"Fetching Marketstack EOD: {url}")
        symbol_count = len(symbols.split(","))
        # Calculate date_from as today - limit days in yyyy-mm-dd format
        date_from = (datetime.now() - timedelta(days=limit)).date().isoformat()
        logger.info(f"Fetching data from date: {date_from}")
        
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params={
                "access_key": MARKETSTACK_API_KEY, 
                "symbols": symbols, 
                "date_from": date_from,
                "limit": limit*symbol_count
            })
            r.raise_for_status()
            return r.json()

    async def fetch_marketstack_company_info(self, url: str = MARKETSTACK_COMPANY_INFO_URL, ticker: str = "TUPRS.IS") -> Dict[str, Any]:
        logger.info(f"Fetching Marketstack Company Info: {url} for ticker: {ticker}")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params={
                "access_key": MARKETSTACK_API_KEY, 
                "ticker": ticker
            })
            r.raise_for_status()
            return r.json()

    def upsert_eod_batch(self, payload: Dict[str, Any], limit: int = 1000) -> int:
        data: List[Dict[str, Any]] = payload.get("data", [])
        saved = 0
        with sqlite3.connect(self.db_path) as conn:
            previous_item = data[0]
            for item in data:
                try:
                    symbol = item.get("symbol")
                    date_str = item.get("date")
                    # Normalize date to YYYY-MM-DD
                    date_norm = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date().isoformat()

                    if limit >= 500 and round(item.get("close") / previous_item.get("close"), 2) >= 1.7:
                        split_factor = self.__get_split_factor(symbol, date_norm)
                        logger.info(f"Split factor found for {symbol} on {date_norm} with factor: {split_factor}")
                        if split_factor == 1:
                            # Remove the previous item that was already upserted since it needs split adjustment
                            conn.execute(
                                "DELETE FROM eod_quotes WHERE symbol = ? AND date = ?",
                                (symbol, datetime.fromisoformat(previous_item.get("date").replace("Z", "+00:00")).date().isoformat())
                            )
                            previous_item = item
                            continue
                        item["open"] = item.get("open") / split_factor
                        item["high"] = item.get("high") / split_factor
                        item["low"] = item.get("low") / split_factor
                        item["close"] = item.get("close") / split_factor
                        item["volume"] = item.get("volume") * split_factor

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO eod_quotes(
                            symbol, date, open, high, low, close, volume, raw_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            symbol,
                            date_norm,
                            item["open"],
                            item["high"],
                            item["low"],
                            item["close"],
                            item["volume"],
                            json.dumps(item, ensure_ascii=False),
                        ),
                    )
                    saved += 1
                    previous_item = item
                except Exception as e:
                    logger.error(f"Failed to upsert EOD row: {e}")
            conn.commit()
        logger.info(f"Saved {saved} EOD rows")
        logger.info(f"Saved EOD rows: {data}")
        return saved

    def upsert_company_info(self, payload: Dict[str, Any]) -> int:
        """
        Upsert company info for a single company from the API response format.
        Expected payload format: {"data": {...company_data...}}
        """
        company_data = payload.get("data", {})
        if not company_data:
            logger.warning("No company data found in payload")
            return 0
            
        try:
            # Extract data from the API response format
            symbol = company_data.get("ticker", "")
            name = company_data.get("name", "")
            sector = company_data.get("sector", "")
            industry = company_data.get("industry", "")
            fulltime_employees = company_data.get("full_time_employees", "")
            description = company_data.get("about", "")
            website = company_data.get("website", "")
            exchange_code = company_data.get("exchange_code", "")
            
            # Format employees count (e.g., "12368" -> "12K")
            if fulltime_employees and fulltime_employees.isdigit():
                emp_count = int(fulltime_employees)
                if emp_count >= 1000:
                    fulltime_employees = f"{emp_count // 1000}K"
            
            # Clean up sector (remove extra commas and spaces)
            if sector:
                sector = sector.split(',')[0].strip()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO company_info(
                        symbol, name, exchange, currency, country, sector, industry, 
                        website, description, logo, fulltime_employees, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        name,
                        exchange_code,
                        "TRY",  # Default currency for Turkish stocks
                        "TR",   # Default country for Turkish stocks
                        sector,
                        industry,
                        website,
                        description,
                        None,  # logo
                        fulltime_employees,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                conn.commit()
            
            logger.info(f"Saved company info for {symbol}: {name}")
            return 1
            
        except Exception as e:
            logger.error(f"Failed to upsert company info: {e}")
            return 0

    def has_any_company_info(self) -> bool:
        """Return True if at least one company_info row exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT 1 FROM company_info LIMIT 1")
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check company_info existence: {e}")
            return False

    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Get company info for a specific symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT symbol, name, exchange, currency, country, sector, industry, 
                           website, description, logo, fulltime_employees, raw_json
                    FROM company_info 
                    WHERE symbol = ?
                    """,
                    (symbol,)
                )
                row = cursor.fetchone()
                
                if row:
                    return {
                        "symbol": row[0],
                        "name": row[1],
                        "exchange": row[2],
                        "currency": row[3],
                        "country": row[4],
                        "sector": row[5],
                        "industry": row[6],
                        "website": row[7],
                        "description": row[8],
                        "logo": row[9],
                        "fulltime_employees": row[10],
                        "raw_json": row[11]
                    }
                return {}
        except Exception as e:
            logger.error(f"Failed to get company info for {symbol}: {e}")
            return {}

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

    def get_gainers_losers_active(
        self,
        symbols: List[str],
        limit: int = 30,
        chart_num: int = 8,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Compute top gainers, losers, and most active (by absolute pct change) stocks
        over the last `limit` days.

        Returns a dict with three lists: `gainers`, `losers`, `active`.
        Each item contains only `{ symbol, change_percent }` as requested.
        """
        cutoff_date = (datetime.now() - timedelta(days=limit)).date().isoformat()

        changes: List[Tuple[str, float]] = []  # (symbol, change_percent)
        with sqlite3.connect(self.db_path) as conn:
            for symbol in symbols:
                cur = conn.execute(
                    """
                    SELECT raw_json FROM eod_quotes
                    WHERE symbol = ? AND date >= ?
                    ORDER BY date DESC
                    """,
                    (symbol, cutoff_date),
                )
                rows = cur.fetchall()
                if len(rows) < 2:
                    continue

                data = [json.loads(r[0]) for r in rows]
                first_close = data[-1].get("close")
                last_close = data[0].get("close")
                if not first_close or not last_close:
                    continue
                try:
                    change_percent = ((last_close - first_close) / first_close) * 100
                except Exception:
                    continue

                changes.append((symbol, float(change_percent)))

        # Gainers: highest positive change
        gainers = [
            {"symbol": sym, "change_percent": ch}
            for sym, ch in sorted(changes, key=lambda x: x[1], reverse=True)
            if ch > 0
        ][:chart_num]

        # Losers: most negative change
        losers = [
            {"symbol": sym, "change_percent": ch}
            for sym, ch in sorted(changes, key=lambda x: x[1])
            if ch < 0
        ][:chart_num]

        # Active: largest absolute change (positive or negative)
        active = [
            {"symbol": sym, "change_percent": ch}
            for sym, ch in sorted(changes, key=lambda x: abs(x[1]), reverse=True)
        ][:chart_num]

        logger.info(
            "GLA computed - gainers: %s, losers: %s, active: %s",
            [g["symbol"] for g in gainers],
            [l["symbol"] for l in losers],
            [a["symbol"] for a in active],
        )

        return {"gainers": gainers, "losers": losers, "active": active}


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
    
    def __get_split_factor(self, symbol: str, date: str) -> float:
        if symbol not in SPLIT_FACTOR_MAP:
            return 1
            
        split_entries = SPLIT_FACTOR_MAP[symbol]
        target_date = datetime.fromisoformat(date).date()
        
        closest_split = None
        closest_diff = None
        for split_entry in split_entries:
            for split_date_str, split_ratio in split_entry.items():
                split_date = datetime.fromisoformat(split_date_str).date()
                diff = abs((target_date - split_date).days)
                
                if closest_diff is None or diff < closest_diff:
                    closest_diff = diff
                    closest_split = split_ratio
        
        if closest_split:
            # Extract the split factor from ratio string (e.g., "2:1" -> 2)
            return float(closest_split.split(":")[0])


        return 1

store = MarketDataStore()

async def init_market_data() -> None:
    # Run only once: if company_info table already has data, skip initialization
    try:
        if store.has_any_company_info():
            logger.info("Company info already present. Skipping init_market_data().")
            return
    except Exception:
        # In case of any error, proceed cautiously with initialization
        logger.warn("Could not verify company_info presence; proceeding with initialization.")
    logger.info("Initializing company info...")
    for ticker in MARKETSTACK_TICKERS:
        payload = await store.fetch_marketstack_company_info(ticker=ticker)
        store.upsert_company_info(payload)
    await refresh_eod(symbols=",".join(MARKETSTACK_TICKERS), limit=1000)


        
async def refresh_eod(symbols: str = "TUPRS.IS", limit: int = 7) -> int:
    logger.info(f"Refreshing EOD for symbols: {symbols[:10]}... with limit: {limit}")
    total_data_point_num = len(symbols.split(",")) * limit
    symbol_list = symbols.split(",")

    if limit > 1000:
        limit = 1000

    if total_data_point_num > 1000:
        current_symbol_index = 0
        while current_symbol_index < len(symbol_list):
            for i in range((1000 // limit)):
                payload = await store.fetch_marketstack_eod(symbols=symbol_list[current_symbol_index], limit=limit)
                store.upsert_eod_batch(payload, limit=limit)
                current_symbol_index += 1
        return total_data_point_num



    payload = await store.fetch_marketstack_eod(symbols=symbols, limit=limit)
    return store.upsert_eod_batch(payload, limit=limit)



SPLIT_FACTOR_MAP = {
    "AEFES.IS": [{"2025-06-26": "10:1"}],
    "ASELS.IS": [{"2023-08-25": "2:1"}],
    "CIMSA.IS": [{"2023-09-29": "7:1"}],
    "EREGL.IS": [{"2024-11-27": "2:1"}],
    "FROTO.IS": [{"2025-05-07": "10:1"}],
    "ISCTR.IS": [{"2024-02-27": "2.5:1"}],
    "PGSUS.IS": [{"2024-05-14": "4.8876:1"}],
    "SASA.IS": [{"2024-08-12": "8:1"}, {"2023-05-23": "2.3:1"}],
}