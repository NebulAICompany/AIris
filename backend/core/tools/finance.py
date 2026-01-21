import httpx
import sys
import json
import time
from datetime import date
from pathlib import Path
from typing import Dict, Any
from langchain_core.tools import tool
import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.shared.constants import (
    CHARTS_DIR,
    CHART_DATA_FILE,
    MARKETSTACK_API_KEY,
    MARKETSTACK_BASE_URL,
)


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
            return {"error": f"HTTP hata: {e.response.status_code} - {e.response.text}"}
        except httpx.RequestError as e:
            attempt += 1
            if attempt < retries:
                wait_time = 2 ** (attempt - 1)
                time.sleep(wait_time)
            else:
                return {"error": f"İstek hatası: {str(e)}"}
        except Exception as e:
            return {"error": f"Beklenmeyen hata: {str(e)}"}


# ============================================================================
# END-OF-DAY DATA METHODS
# ============================================================================


@tool
def get_eod_data(
    symbols: str,
    date_from: str = None,
    date_to: str = None,
    exchange: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch end-of-day data for one or multiple stock tickers from Marketstack.

    Required:
        symbols (str): One or multiple comma-separated stock symbols (e.g., "AAPL" or "AAPL,MSFT")

    Optional:
        date_from (str): Filter results from date in YYYY-MM-DD format (defaults to today if not provided)
        date_to (str): Filter results to date in YYYY-MM-DD format (defaults to today if not provided)
        exchange (str): Filter by exchange MIC code (e.g., "XNAS")
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: End-of-day data with OHLCV values for specified symbols
    """
    today = date.today().strftime("%Y-%m-%d")
    date_from = date_from or today
    date_to = date_to or today

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


# ============================================================================
# INTRADAY DATA METHODS
# ============================================================================


@tool
def get_intraday_data(
    symbols: str,
    interval: str = "1min",
    date_from: str = None,
    date_to: str = None,
    exchange: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch intraday data for one or multiple stock tickers from Marketstack.

    Required:
        symbols (str): One or multiple comma-separated stock symbols (e.g., "AAPL" or "AAPL,MSFT")

    Optional:
        interval (str): Data interval - "1min", "5min", "15min", "30min", "1hour", "3hour", "6hour", "12hour", "24hour"
        date_from (str): Filter results from date in YYYY-MM-DD format (defaults to today if not provided)
        date_to (str): Filter results to date in YYYY-MM-DD format (defaults to today if not provided)
        exchange (str): Filter by exchange MIC code (e.g., "XNAS")
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Intraday data with OHLCV values for specified symbols
    """
    today = date.today().strftime("%Y-%m-%d")
    date_from = date_from or today
    date_to = date_to or today

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


@tool
def get_exchanges(
    search: str = None,
    country: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch list of available exchanges from Marketstack.

    Optional:
        search (str): Search term for exchange name
        country (str): Filter by country code (e.g., "US")
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: List of available exchanges with their information
    """
    params = {
        **({"search": search} if search else {}),
        **({"country": country} if country else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("exchanges", params)


@tool
def get_exchange_info(
    exchange: str,
):
    """
    Fetch detailed information for a specific exchange from Marketstack.

    Required:
        exchange (str): Exchange MIC code (e.g., "XNAS")

    Returns:
        dict: Detailed information about the specified exchange
    """
    return make_request(f"exchanges/{exchange}", {})


# ============================================================================
# CURRENCIES AND TIMEZONES METHODS
# ============================================================================


@tool
def get_currencies(
    search: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch list of available currencies from Marketstack.

    Optional:
        search (str): Search term for currency name or code
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: List of available currencies with their information
    """
    params = {
        **({"search": search} if search else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("currencies", params)


@tool
def get_timezones(
    search: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch list of available timezones from Marketstack.

    Optional:
        search (str): Search term for timezone name
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: List of available timezones with their information
    """
    params = {
        **({"search": search} if search else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("timezones", params)


# ============================================================================
# SPLITS AND DIVIDENDS METHODS
# ============================================================================


@tool
def get_splits_data(
    symbols: str,
    date_from: str = None,
    date_to: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch stock splits data for one or multiple stock tickers.

    Required:
        symbols (str): One or multiple comma-separated stock symbols (e.g., "AAPL" or "AAPL,MSFT")

    Optional:
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Stock splits data with split factors and dates
    """
    params = {
        "symbols": symbols,
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return make_request("splits", params)


@tool
def get_dividends_data(
    symbols: str,
    date_from: str = None,
    date_to: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch dividends data for one or multiple stock tickers.

    Required:
        symbols (str): One or multiple comma-separated stock symbols (e.g., "AAPL" or "AAPL,MSFT")

    Optional:
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Dividends data with payment dates and amounts
    """
    params = {
        "symbols": symbols,
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return make_request("dividends", params)


# ============================================================================
# STOCK MARKET INDEXES METHODS (Updated)
# ============================================================================


@tool
def get_index_list(
    limit: int = 100,
    offset: int = 0,
):
    """
    Get list of available stock market indexes.
    Available for Basic Plan and higher.

    Optional:
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: List of available stock market indexes
    """
    params = {
        "limit": limit,
        "offset": offset,
    }
    return make_request("indexlist", params)


@tool
def get_index_info(
    index: str,
):
    """
    Get detailed information for a specific stock market index.
    Available for Basic Plan and higher.

    Required:
        index (str): Index code (e.g., "australia_all_ordinaries")

    Returns:
        dict: Detailed information about the specified stock market index
    """
    params = {
        "index": index,
    }
    return make_request("indexinfo", params)


# ============================================================================
# TICKERS METHODS (Updated to match documentation)
# ============================================================================


@tool
def get_tickers_list(
    search: str = None,
    exchange: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get the full list of supported tickers from Marketstack.

    Optional:
        search (str): Search stock tickers by name or ticker symbol
        exchange (str): Search stock tickers by exchange MIC
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: List of available tickers with their information
    """
    params = {
        **({"search": search} if search else {}),
        **({"exchange": exchange} if exchange else {}),
        "limit": limit,
        "offset": offset,
    }
    return make_request("tickerslist", params)


@tool
def get_ticker_info_detailed(
    ticker: str,
):
    """
    Get detailed information about a specific ticker.

    Required:
        ticker (str): Stock ticker symbol (e.g., "MSFT")

    Returns:
        dict: Detailed information about the ticker including executives, addresses, etc.
    """
    params = {
        "ticker": ticker,
    }
    return make_request("tickerinfo", params)


# ============================================================================
# CHART MANAGEMENT FUNCTIONS
# ============================================================================


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


# ============================================================================
# TECHNICAL INDICATORS HELPERS
# ============================================================================


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
