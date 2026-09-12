import httpx
import sys
import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_core.tools import tool
import pandas as pd
from backend.shared.logger import get_logger
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.shared.constants import (
    CHARTS_DIR,
    CHART_DATA_FILE,
    MARKETSTACK_API_KEY,
    MARKETSTACK_BASE_URL,
)

logger = get_logger("FINANCE")
def make_request(
    endpoint: str, params: Dict[str, Any], retries: int = 3, timeout: float = 10.0
) -> Dict[str, Any]:
    """Sends a synchronous request to the Marketstack API."""
    params["access_key"] = MARKETSTACK_API_KEY
    url = f"{MARKETSTACK_BASE_URL}/{endpoint}"

    attempt = 0
    while attempt < retries:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except httpx.RequestError as e:
            attempt += 1
            if attempt < retries:
                wait_time = 2 ** (attempt - 1)
                time.sleep(wait_time)
            else:
                return {"error": f"Request error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


@tool(parse_docstring=True)
def get_eod_data(
    symbols: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    exchange: Optional[str] = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Fetch end-of-day stock data from Marketstack.

    Args:
        symbols: One or more comma-separated stock symbols (for example, "AAPL" or "AAPL,MSFT").
        date_from: Start date in YYYY-MM-DD format for filtering results. If not provided, 90 days ago will be used.
        date_to: End date in YYYY-MM-DD format for filtering results. If not provided, today's date will be used.
        exchange: Exchange MIC code to filter by (for example, "XNAS").
        sort: Sort order for results, "DESC" (default) or "ASC".
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    today = date.today()
    if date_from is None:
        date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = today.strftime("%Y-%m-%d")
    params = {
        "symbols": symbols,
        "date_from": date_from,
        "date_to": date_to,
        **({"exchange": exchange} if exchange else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return make_request("eod", params)


#NOT USABLE DUE TO MARKETSTACK API LIMITATIONS
@tool(parse_docstring=True)
def get_intraday_data(
    symbols: str,
    interval: str = "1min",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    exchange: Optional[str] = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Fetch intraday stock data from Marketstack.

    Args:
        symbols: One or more comma-separated stock symbols (for example, "AAPL" or "AAPL,MSFT").
            (for example, "AAPL" or "AAPL,MSFT").
        interval: Data interval such as "1min", "5min", "15min", "30min",
            "1hour", "3hour", "6hour", "12hour", or "24hour".
        date_from: Start date in YYYY-MM-DD format for filtering results. If not provided, 90 days ago will be used.
        date_to: End date in YYYY-MM-DD format for filtering results. If not provided, today's date will be used.
        exchange: Exchange MIC code to filter by (for example, "XNAS").
        sort: Sort order for results, "DESC" (default) or "ASC".
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    today = date.today()
    if date_from is None:
        date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = today.strftime("%Y-%m-%d")

    params = {
        "symbols": symbols,
        "interval": interval,
        "date_from": date_from,
        "date_to": date_to,
        **({"exchange": exchange} if exchange else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return make_request("intraday", params)

@tool(parse_docstring=True)
def get_exchanges(
    search: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Fetch a list of available exchanges from Marketstack.

    Args:
        search: Optional search term to filter exchanges by name.
        country: Optional country code to filter exchanges (for example, "US").
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    params = {
        **({"search": search} if search else {}),
        **({"country": country} if country else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("exchanges", params)

@tool(parse_docstring=True)
def get_exchange_info(exchange: str) -> dict:
    """Fetch detailed information for a specific exchange from Marketstack.

    Args:
        exchange: Exchange MIC code (for example, "XNAS").
    """
    return make_request(f"exchanges/{exchange}", {})


@tool(parse_docstring=True)
def get_currencies(
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Fetch a list of available currencies from Marketstack.

    Args:
        search: Optional search term to filter currencies by name or code.
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning. (default 0)
    """
    params = {
        **({"search": search} if search else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("currencies", params)


@tool(parse_docstring=True)
def get_timezones(
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Fetch a list of available timezones from Marketstack.

    Args:
        search: Optional search term to filter timezones by name.
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    params = {
        **({"search": search} if search else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("timezones", params)


@tool(parse_docstring=True)
def get_splits_data(
    symbols: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Fetch stock split data for one or more tickers.

    Args:
        symbols: One or more comma-separated stock symbols (for example, "AAPL" or "AAPL,MSFT").
        date_from: Start date in YYYY-MM-DD format for filtering results. If not provided, 90 days ago will be used.
        date_to: End date in YYYY-MM-DD format for filtering results. If not provided, today's date will be used.
        sort: Sort order for results, "DESC" (default) or "ASC".
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    today = date.today()
    if date_from is None:
        date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = today.strftime("%Y-%m-%d")
    params = {
        "symbols": symbols,
        "date_from": date_from,
        "date_to": date_to,
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return make_request("splits", params)


@tool(parse_docstring=True)
def get_dividends_data(
    symbols: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Fetch dividend data for one or more stock tickers.

    Args:
        symbols: One or more comma-separated stock symbols (for example, "AAPL" or "AAPL,MSFT").
        date_from: Start date in YYYY-MM-DD format for filtering results. If not provided, 90 days ago will be used.
        date_to: End date in YYYY-MM-DD format for filtering results. If not provided, today's date will be used.
        sort: Sort order for results, "DESC" (default) or "ASC".
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    today = date.today()
    if date_from is None:
        date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = today.strftime("%Y-%m-%d")
    params = {
        "symbols": symbols,
        "date_from": date_from,
        "date_to": date_to,
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return make_request("dividends", params)


@tool(parse_docstring=True)
def get_index_list(
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Get a list of available stock market indexes.

    Args:
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    params = {
        "limit": limit,
        "offset": offset,
    }
    return make_request("indexlist", params)


@tool(parse_docstring=True)
def get_index_info(index: str) -> dict:
    """Get detailed information for a specific stock market index.

    Args:
        index: Index code (for example, "australia_all_ordinaries").
    """
    params = {
        "index": index,
    }
    return make_request("indexinfo", params)


@tool(parse_docstring=True)
def get_tickers_list(
    search: Optional[str] = None,
    exchange: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Get the list of supported stock tickers from Marketstack.

    Args:
        search: Optional search term to filter tickers by name or symbol.
        exchange: Optional exchange MIC code to filter tickers by exchange.
        limit: Maximum number of results to return per page (default 100, max 1000).
        offset: Number of results to skip from the beginning.
    """
    params = {
        **({"search": search} if search else {}),
        **({"exchange": exchange} if exchange else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("tickerslist", params)


@tool(parse_docstring=True)
def get_ticker_info_detailed(ticker: str) -> dict:
    """Get detailed information about a specific stock ticker.

    Args:
        ticker: Stock ticker symbol (for example, "MSFT").
    """
    params = {
        "ticker": ticker,
    }
    return make_request("tickerinfo", params)


def get_chart_datas():
    """Get chart data from JSON file storage"""
    try:
        if not CHART_DATA_FILE.exists():
            return []

        with open(CHART_DATA_FILE, "r", encoding="utf-8") as f:
            chart_data = json.load(f)

        return chart_data
    except Exception as e:
        return []


def set_chart_data(data):
    """Set chart data to JSON file storage - overwrites file each time"""
    try:
        # Ensure CHARTS_DIR exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        # Overwrite file with new chart data (don't append)
        with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([data], f, ensure_ascii=False, indent=2)

    except Exception as e:
        pass


def clear_chart_datas():
    """Clear chart data from JSON file storage"""
    try:
        if CHART_DATA_FILE.exists():
            # Clear the file by writing an empty list
            with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        else:
            pass
    except Exception as e:
        pass


def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return data.rolling(window=window, min_periods=1).mean()


def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data.ewm(span=window, adjust=False).mean()


def calculate_bollinger_bands(data: pd.Series, window: int = 20, num_std: float = 2):
    """Calculate Bollinger Bands"""
    sma = calculate_sma(data, window)
    std = data.rolling(window=window, min_periods=1).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    return upper_band, sma, lower_band


def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=1).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Calculate MACD"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
