import httpx
import sys
import json
from pathlib import Path
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import uuid

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.shared.constants import (
    CHARTS_DIR,
    CHART_DATA_FILE,
    MARKETSTACK_EOD_API_KEY,
    MARKETSTACK_BASE_URL,
)


# Setup logging for chart operations using loguru
from loguru import logger

chart_logger = logger.bind(name="CHART_OPERATIONS")

mcp = FastMCP("finance")


async def make_request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Marketstack API'sine async istek gönder"""
    params["access_key"] = MARKETSTACK_EOD_API_KEY
    url = f"{MARKETSTACK_BASE_URL}/{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# END-OF-DAY DATA METHODS
# ============================================================================


@mcp.tool()
async def get_eod_data(
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
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        exchange (str): Filter by exchange MIC code (e.g., "XNAS")
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: End-of-day data with OHLCV values for specified symbols
    """
    params = {
        "symbols": symbols,
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        **({"exchange": exchange} if exchange else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request("eod", params)


@mcp.tool()
async def get_eod_latest(
    symbols: str,
    exchange: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch latest end-of-day data for one or multiple stock tickers from Marketstack.

    Required:
        symbols (str): One or multiple comma-separated stock symbols (e.g., "AAPL" or "AAPL,MSFT")

    Optional:
        exchange (str): Filter by exchange MIC code (e.g., "XNAS")
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Latest end-of-day data with OHLCV values for specified symbols
    """
    params = {
        "symbols": symbols,
        **({"exchange": exchange} if exchange else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request("eod/latest", params)


@mcp.tool()
async def get_eod_date(
    symbols: str,
    date: str,
    exchange: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch end-of-day data for a specific date from Marketstack.

    Required:
        symbols (str): One or multiple comma-separated stock symbols (e.g., "AAPL" or "AAPL,MSFT")
        date (str): Date in YYYY-MM-DD format (e.g., "2020-01-01")

    Optional:
        exchange (str): Filter by exchange MIC code (e.g., "XNAS")
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: End-of-day data for specified date and symbols
    """
    params = {
        "symbols": symbols,
        **({"exchange": exchange} if exchange else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request(f"eod/{date}", params)


# ============================================================================
# INTRADAY DATA METHODS
# ============================================================================


@mcp.tool()
async def get_intraday_data(
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
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        exchange (str): Filter by exchange MIC code (e.g., "XNAS")
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Intraday data with OHLCV values for specified symbols
    """
    params = {
        "symbols": symbols,
        "interval": interval,
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        **({"exchange": exchange} if exchange else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request("intraday", params)


@mcp.tool()
async def get_intraday_latest(
    symbols: str,
    interval: str = "1min",
    exchange: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch latest intraday data for one or multiple stock tickers from Marketstack.

    Required:
        symbols (str): One or multiple comma-separated stock symbols (e.g., "AAPL" or "AAPL,MSFT")

    Optional:
        interval (str): Data interval - "1min", "5min", "15min", "30min", "1hour", "3hour", "6hour", "12hour", "24hour"
        exchange (str): Filter by exchange MIC code (e.g., "XNAS")
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Latest intraday data with OHLCV values for specified symbols
    """
    params = {
        "symbols": symbols,
        "interval": interval,
        **({"exchange": exchange} if exchange else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request("intraday/latest", params)


# ============================================================================
# TICKERS AND EXCHANGES METHODS
# ============================================================================


@mcp.tool()
async def get_ticker_eod_data(
    symbol: str,
    date_from: str = None,
    date_to: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch end-of-day data for a specific ticker using tickers endpoint.

    Required:
        symbol (str): Stock ticker symbol (e.g., "AAPL")

    Optional:
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: End-of-day data for the specified ticker
    """
    params = {
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request(f"tickers/{symbol}/eod", params)


@mcp.tool()
async def get_ticker_intraday_data(
    symbol: str,
    interval: str = "1hour",
    date_from: str = None,
    date_to: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
    after_hours: bool = False,
):
    """
    Fetch intraday data for a specific ticker using tickers endpoint.

    Required:
        symbol (str): Stock ticker symbol (e.g., "AAPL")

    Optional:
        interval (str): Data interval - "1min", "5min", "10min", "15min", "30min", "1hour", "3hour", "6hour", "12hour", "24hour"
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip
        after_hours (bool): Include pre and post market data if available

    Returns:
        dict: Intraday data for the specified ticker
    """
    params = {
        "interval": interval,
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
        "after_hours": str(after_hours).lower(),
    }
    return await make_request(f"tickers/{symbol}/intraday", params)


@mcp.tool()
async def get_ticker_splits_data(
    symbol: str,
    date_from: str = None,
    date_to: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch splits data for a specific ticker using tickers endpoint.

    Required:
        symbol (str): Stock ticker symbol (e.g., "AAPL")

    Optional:
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Splits data for the specified ticker
    """
    params = {
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request(f"tickers/{symbol}/splits", params)


@mcp.tool()
async def get_ticker_dividends_data(
    symbol: str,
    date_from: str = None,
    date_to: str = None,
    sort: str = "DESC",
    limit: int = 100,
    offset: int = 0,
):
    """
    Fetch dividends data for a specific ticker using tickers endpoint.

    Required:
        symbol (str): Stock ticker symbol (e.g., "AAPL")

    Optional:
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format
        sort (str): Sort order - "DESC" (default) or "ASC"
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: Dividends data for the specified ticker
    """
    params = {
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    return await make_request(f"tickers/{symbol}/dividends", params)


@mcp.tool()
async def get_exchanges(
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
    return await make_request("exchanges", params)


@mcp.tool()
async def get_exchange_info(
    exchange: str,
):
    """
    Fetch detailed information for a specific exchange from Marketstack.

    Required:
        exchange (str): Exchange MIC code (e.g., "XNAS")

    Returns:
        dict: Detailed information about the specified exchange
    """
    return await make_request(f"exchanges/{exchange}", {})


# ============================================================================
# CURRENCIES AND TIMEZONES METHODS
# ============================================================================


@mcp.tool()
async def get_currencies(
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
    return await make_request("currencies", params)


@mcp.tool()
async def get_timezones(
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
    return await make_request("timezones", params)


# ============================================================================
# BONDS METHODS
# ============================================================================


@mcp.tool()
async def get_bond_list(
    limit: int = 100,
    offset: int = 0,
):
    """
    Get list of supported countries for bonds data.
    Available for Basic Plan and higher.

    Optional:
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: List of supported countries for bonds
    """
    params = {
        "limit": limit,
        "offset": offset,
    }
    return await make_request("bondlist", params)


@mcp.tool()
async def get_bond_info(
    country: str,
):
    """
    Get real-time government bond data for a specific country.
    Available for Basic Plan and higher.

    Required:
        country (str): Country name (e.g., "kenya" or "united%20states")

    Returns:
        dict: Government bond data including yield and price changes
    """
    params = {
        "country": country,
    }
    return await make_request("bond", params)


# ============================================================================
# ETF HOLDINGS METHODS
# ============================================================================


@mcp.tool()
async def get_etf_list(
    list_type: str = "ticker",
    limit: int = 100,
    offset: int = 0,
):
    """
    Get list of supported ETF tickers.
    Available for Basic Plan and higher. Call count multiplier: 20.

    Required:
        list_type (str): Type of list to retrieve (currently only "ticker" supported)

    Optional:
        limit (int): Number of results per page (max 1000)
        offset (int): Number of results to skip

    Returns:
        dict: List of supported ETF tickers
    """
    params = {
        "list": list_type,
        "limit": limit,
        "offset": offset,
    }
    return await make_request("etflist", params)


@mcp.tool()
async def get_etf_holdings(
    ticker: str,
    date_from: str = None,
    date_to: str = None,
):
    """
    Get complete ETF holdings data based on ticker identifier.
    Available for Basic Plan and higher. Call count multiplier: 20.

    Required:
        ticker (str): ETF ticker symbol (e.g., "SPY")

    Optional:
        date_from (str): Filter results from date in YYYY-MM-DD format
        date_to (str): Filter results to date in YYYY-MM-DD format

    Returns:
        dict: Complete ETF holdings data with fund information and holdings details
    """
    params = {
        "ticker": ticker,
        **({"date_from": date_from} if date_from else {}),
        **({"date_to": date_to} if date_to else {}),
    }
    return await make_request("etfholdings", params)


# ============================================================================
# SPLITS AND DIVIDENDS METHODS
# ============================================================================


@mcp.tool()
async def get_splits_data(
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
    return await make_request("splits", params)


@mcp.tool()
async def get_dividends_data(
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
    return await make_request("dividends", params)


# ============================================================================
# STOCK MARKET INDEXES METHODS (Updated)
# ============================================================================


@mcp.tool()
async def get_index_list(
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
    return await make_request("indexlist", params)


@mcp.tool()
async def get_index_info(
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
    return await make_request("indexinfo", params)


# ============================================================================
# TICKERS METHODS (Updated to match documentation)
# ============================================================================


@mcp.tool()
async def get_tickers_list(
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
    return await make_request("tickerslist", params)


@mcp.tool()
async def get_ticker_info_detailed(
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
    return await make_request("tickerinfo", params)


# ============================================================================
# HIGHER PLAN METHODS (COMMENTED OUT - NOT AVAILABLE FOR BASIC PLAN)
# ============================================================================

# ============================================================================
# PROFESSIONAL PLAN METHODS (403 Forbidden for Free/Basic Plans)
# ============================================================================

# @mcp.tool()
# async def get_realtime_stock_price(
#     ticker: str,
#     exchange: str = None,
# ):
#     """
#     Fetch real-time stock price for a specific ticker from Marketstack.
#     Available for Professional and Higher plans. Rate limit: 1 API call per minute.

#     Required:
#         ticker (str): Stock ticker symbol (e.g., "AAPL")

#     Optional:
#         exchange (str): Filter by exchange name (e.g., "nasdaq")

#     Returns:
#         dict: Real-time stock price data for the specified ticker
#         Note: Returns 403 Forbidden for Free/Basic plans
#     """
#     params = {
#         "ticker": ticker,
#         **({"exchange": exchange} if exchange else {}),
#     }
#     return await make_request("stockprice", params)


# @mcp.tool()
# async def get_commodity_prices(
#     commodity_name: str,
# ):
#     """
#     Get commodity prices for 70+ world-known commodities.
#     Available for Professional and Higher plans. Rate limit: 1 API call per minute.

#     Required:
#         commodity_name (str): Commodity name (e.g., "gold", "aluminum")

#     Returns:
#         dict: Current commodity price data with price changes and forecasts
#         Note: Returns 403 Forbidden for Free/Basic plans
#     """
#     params = {
#         "commodity_name": commodity_name,
#     }
#     return await make_request("commodities", params)


# @mcp.tool()
# async def get_commodities_history(
#     commodity_name: str,
#     date_from: str = None,
#     date_to: str = None,
#     frequency: str = "day",
# ):
#     """
#     Get historical commodity prices for up to 15 years.
#     Available for Professional and Higher plans. Rate limit: 1 API call per minute.

#     Required:
#         commodity_name (str): Commodity name (e.g., "aluminum", "brent")

#     Optional:
#         date_from (str): Start date in YYYY-MM-DD format
#         date_to (str): End date in YYYY-MM-DD format
#         frequency (str): "day" or "month" (default: "day")

#     Returns:
#         dict: Historical commodity price data
#         Note: Returns 403 Forbidden for Free/Basic plans
#     """
#     params = {
#         "commodity_name": commodity_name,
#         **({"date_from": date_from} if date_from else {}),
#         **({"date_to": date_to} if date_to else {}),
#         "frequency": frequency,
#     }
#     return await make_request("commoditieshistory", params)


# ============================================================================
# BUSINESS PLAN METHODS (403 Forbidden for Free/Basic/Professional Plans)
# ============================================================================

# @mcp.tool()
# async def get_company_ratings(
#     ticker: str,
#     date_from: str = None,
#     date_to: str = None,
#     rated: str = None,
# ):
#     """
#     Get current and historical analyst buy/sell/hold ratings.
#     Available for Business and Higher plans. Rate limit: 1 API call per minute.

#     Required:
#         ticker (str): Stock ticker symbol (e.g., "AAPL")

#     Optional:
#         date_from (str): Start date in YYYY-MM-DD format
#         date_to (str): End date in YYYY-MM-DD format
#         rated (str): Filter by rating - "buy", "sell", or "hold"

#     Returns:
#         dict: Company ratings with analyst consensus and individual ratings
#         Note: Returns 403 Forbidden for Free/Basic/Professional plans
#     """
#     params = {
#         "ticker": ticker,
#         **({"date_from": date_from} if date_from else {}),
#         **({"date_to": date_to} if date_to else {}),
#         **({"rated": rated} if rated else {}),
#     }
#     return await make_request("companyratings", params)


# @mcp.tool()
# async def find_cik_by_company_name_edgar(
#     company_name: str,
#     limit: int = 100,
#     offset: int = 0,
# ):
#     """
#     Find CIK code by company name using EDGAR integration.
#     Available for Business Plan only.

#     Required:
#         company_name (str): Company name to search for (minimum 3 letters)

#     Optional:
#         limit (int): Number of results per page (max 1000)
#         offset (int): Number of results to skip

#     Returns:
#         dict: CIK codes matching the company name
#     """
#     params = {
#         "company_name": company_name,
#         "limit": limit,
#         "offset": offset,
#     }
#     return await make_request("cik_code", params)


# @mcp.tool()
# async def find_company_name_by_cik_edgar(
#     cik_code: str,
# ):
#     """
#     Find company name by CIK code using EDGAR integration.
#     Available for Business Plan only.

#     Required:
#         cik_code (str): 10-digit CIK code including leading zeros

#     Returns:
#         dict: Company information matching the CIK code
#     """
#     params = {
#         "cik_code": cik_code,
#     }
#     return await make_request("company_name", params)


# @mcp.tool()
# async def get_company_submissions_edgar(
#     cik_code: str,
# ):
#     """
#     Get company submission data from EDGAR.
#     Available for Business Plan only.

#     Required:
#         cik_code (str): 10-digit CIK code including leading zeros

#     Returns:
#         dict: Company submission data including filings and metadata
#     """
#     params = {
#         "cik_code": cik_code,
#     }
#     return await make_request("submissions", params)


# @mcp.tool()
# async def get_company_facts_edgar(
#     cik_code: str,
# ):
#     """
#     Get company facts data from EDGAR using XBRL.
#     Available for Business Plan only.

#     Required:
#         cik_code (str): 10-digit CIK code including leading zeros

#     Returns:
#         dict: Company facts data with XBRL taxonomy information
#     """
#     params = {
#         "cik_code": cik_code,
#     }
#     return await make_request("company_facts", params)


# @mcp.tool()
# async def get_company_concepts_accounts_payable(
#     cik_code: str,
# ):
#     """
#     Get company concepts for US GAAP Accounts Payable.
#     Available for Business Plan only.

#     Required:
#         cik_code (str): 10-digit CIK code including leading zeros

#     Returns:
#         dict: Company concepts data for accounts payable
#     """
#     params = {
#         "cik_code": cik_code,
#     }
#     return await make_request("concept/accounts_payable", params)


# @mcp.tool()
# async def get_frames_accounts_payable(
#     frame: str,
#     units: str = "USD",
#     limit: int = 100,
#     offset: int = 0,
# ):
#     """
#     Get frames data for US GAAP Accounts Payable.
#     Available for Business Plan only.

#     Required:
#         frame (str): Frame period (e.g., "CY2009Q3I")

#     Optional:
#         units (str): Unit of measurement (default: "USD")
#         limit (int): Number of results per page (max 1000)
#         offset (int): Number of results to skip

#     Returns:
#         dict: Frames data for accounts payable
#     """
#     params = {
#         "frame": frame,
#         "units": units,
#         "limit": limit,
#         "offset": offset,
#     }
#     return await make_request(f"frames/accounts_payable/{units}", params)


# ============================================================================
# COMPANY DATA METHODS (Legacy - Business Plan Required)
# ============================================================================

# @mcp.tool()
# async def find_cik_by_company_name(
#     company_name: str,
#     limit: int = 100,
#     offset: int = 0,
# ):
#     """
#     Find CIK code by company name using EDGAR integration.
#     Available for Business Plan only.

#     Required:
#         company_name (str): Company name to search for (minimum 3 letters)

#     Optional:
#         limit (int): Number of results per page (max 1000)
#         offset (int): Number of results to skip

#     Returns:
#         dict: CIK codes matching the company name
#     """
#     params = {
#         "company_name": company_name,
#         "limit": limit,
#         "offset": offset,
#     }
#     return await make_request("cik_code", params)


# @mcp.tool()
# async def find_company_name_by_cik(
#     cik: str,
# ):
#     """
#     Find company name by CIK code using EDGAR integration.
#     Available for Business Plan only.

#     Required:
#         cik (str): 10-digit CIK code including leading zeros

#     Returns:
#         dict: Company information matching the CIK code
#     """
#     params = {
#         "cik_code": cik,
#     }
#     return await make_request("company_name", params)


# @mcp.tool()
# async def get_company_submissions(
#     cik: str,
#     form_type: str = None,
#     date_from: str = None,
#     date_to: str = None,
#     limit: int = 100,
#     offset: int = 0,
# ):
#     """
#     Fetch company submission data from Marketstack.

#     Required:
#         cik (str): CIK code of the company

#     Optional:
#         form_type (str): Filter by form type (e.g., "10-K", "10-Q")
#         date_from (str): Filter results from date in YYYY-MM-DD format
#         date_to (str): Filter results to date in YYYY-MM-DD format
#         limit (int): Number of results per page (max 1000)
#         offset (int): Number of results to skip

#     Returns:
#         dict: Company submission data for the specified CIK
#     """
#     params = {
#         **({"form_type": form_type} if form_type else {}),
#         **({"date_from": date_from} if date_from else {}),
#         **({"date_to": date_to} if date_to else {}),
#         "limit": limit,
#         "offset": offset,
#     }
#     return await make_request(f"company_submissions/{cik}/submissions", params)


# @mcp.tool()
# async def get_company_facts(
#     cik: str,
#     taxonomy: str = "us-gaap",
#     tag: str = None,
#     date_from: str = None,
#     date_to: str = None,
#     limit: int = 100,
#     offset: int = 0,
# ):
#     """
#     Fetch company facts data from Marketstack.

#     Required:
#         cik (str): CIK code of the company

#     Optional:
#         taxonomy (str): Taxonomy to use (default: "us-gaap")
#         tag (str): Specific tag to filter by
#         date_from (str): Filter results from date in YYYY-MM-DD format
#         date_to (str): Filter results to date in YYYY-MM-DD format
#         limit (int): Number of results per page (max 1000)
#         offset (int): Number of results to skip

#     Returns:
#         dict: Company facts data for the specified CIK
#     """
#     params = {
#         "taxonomy": taxonomy,
#         **({"tag": tag} if tag else {}),
#         **({"date_from": date_from} if date_from else {}),
#         **({"date_to": date_to} if date_to else {}),
#         "limit": limit,
#         "offset": offset,
#     }
#     return await make_request(f"company_facts/{cik}", params)


# @mcp.tool()
# async def get_company_concepts(
#     cik: str,
#     taxonomy: str = "us-gaap",
#     tag: str = None,
#     date_from: str = None,
#     date_to: str = None,
#     limit: int = 100,
#     offset: int = 0,
# ):
#     """
#     Fetch company concepts data from Marketstack.

#     Required:
#         cik (str): CIK code of the company

#     Optional:
#         taxonomy (str): Taxonomy to use (default: "us-gaap")
#         tag (str): Specific tag to filter by
#         date_from (str): Filter results from date in YYYY-MM-DD format
#         date_to (str): Filter results to date in YYYY-MM-DD format
#         limit (int): Number of results per page (max 1000)
#         offset (int): Number of results to skip

#     Returns:
#         dict: Company concepts data for the specified CIK
#     """
#     params = {
#         "taxonomy": taxonomy,
#         **({"tag": tag} if tag else {}),
#         **({"date_from": date_from} if date_from else {}),
#         **({"date_to": date_to} if date_to else {}),
#         "limit": limit,
#         "offset": offset,
#     }
#     return await make_request(f"company_concepts/{cik}", params)


# @mcp.tool()
# async def get_frames(
#     taxonomy: str = "us-gaap",
#     tag: str = None,
#     ccp: str = None,
#     uom: str = None,
#     date_from: str = None,
#     date_to: str = None,
#     limit: int = 100,
#     offset: int = 0,
# ):
#     """
#     Fetch frames data from Marketstack.

#     Optional:
#         taxonomy (str): Taxonomy to use (default: "us-gaap")
#         tag (str): Specific tag to filter by
#         ccp (str): Company concept period
#         uom (str): Unit of measure
#         date_from (str): Filter results from date in YYYY-MM-DD format
#         date_to (str): Filter results to date in YYYY-MM-DD format
#         limit (int): Number of results per page (max 1000)
#         offset (int): Number of results to skip

#     Returns:
#         dict: Frames data for the specified parameters
#     """
#     params = {
#         "taxonomy": taxonomy,
#         **({"tag": tag} if tag else {}),
#         **({"ccp": ccp} if ccp else {}),
#         **({"uom": uom} if uom else {}),
#         **({"date_from": date_from} if date_from else {}),
#         **({"date_to": date_to} if date_to else {}),
#         "limit": limit,
#         "offset": offset,
#     }
#     return await make_request("frames", params)


# Chart management functions
def get_chart_datas():
    """Get chart data from JSON file storage"""
    try:
        if not CHART_DATA_FILE.exists():
            chart_logger.info(
                "📊 get_chart_datas() called - No chart data file found, returning empty list"
            )
            return []

        with open(CHART_DATA_FILE, "r", encoding="utf-8") as f:
            chart_data = json.load(f)

        for i, chart in enumerate(chart_data):
            chart_logger.info(
                f"  Chart {i+1}: {type(chart)} - Length: {len(str(chart)) if chart else 0}"
            )
        return chart_data
    except Exception as e:
        chart_logger.error(f"❌ Error reading chart data: {e}")
        return []


def set_chart_data(data):
    """Set chart data to JSON file storage - overwrites file each time"""
    try:
        # Ensure CHARTS_DIR exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        chart_logger.info(f"📊 set_chart_data() called with data type: {type(data)}")
        chart_logger.info(f"  Data length: {len(str(data)) if data else 0}")
        chart_logger.info(f"  Data preview: {str(data)[:200] if data else 'None'}...")

        # Overwrite file with new chart data (don't append)
        with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([data], f, ensure_ascii=False, indent=2)

        chart_logger.info(
            f"  Chart data saved to file: {CHART_DATA_FILE} - New chart data written"
        )
    except Exception as e:
        chart_logger.error(f"❌ Error saving chart data: {e}")


def clear_chart_datas():
    """Clear chart data from JSON file storage"""
    try:
        if CHART_DATA_FILE.exists():
            # Clear the file by writing an empty list
            with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

            chart_logger.info(
                f"📊 clear_chart_datas() called - Chart data cleared from file"
            )
        else:
            chart_logger.info(
                f"📊 clear_chart_datas() called - No chart data file found to clear"
            )
    except Exception as e:
        chart_logger.error(f"❌ Error clearing chart data: {e}")


@mcp.tool()
async def create_stock_chart(
    symbols: list,
    period: str = "daily",
    chart_type: str = "candlestick",
    time_range_days: int = 30,
    include_volume: bool = True,
    include_ma: bool = True,
    ma_period: int = 20,
    subplot_layout: str = "single",
):
    """
    Creates comprehensive stock charts using Alpha Vantage data with multiple layout options.
    Implements QuantStart methodology for advanced subplot configurations.

    Required:
        symbols (list): List of stock symbols (e.g., ["AAPL", "MSFT"])

    Optional:
        period (str): "daily" | "weekly" | "monthly" | "intraday"
        chart_type (str): "candlestick" | "line" | "area"
        time_range_days (int): Number of days to display (default: 30)
        include_volume (bool): Whether to show volume chart
        include_ma (bool): Whether to show moving average
        ma_period (int): Moving average period (default: 20)
        subplot_layout (str): "single" | "grid" | "vertical" | "quantstart"
        outputsize (str): "compact" | "full"

    Returns:
        dict: Chart HTML and operation result
    """
    try:
        # Ensure CHARTS_DIR exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        chart_logger.info(f"📁 Charts directory ensured: {CHARTS_DIR}")
        chart_logger.info(f"🚀 Starting chart creation for symbols: {symbols}")

        if len(symbols) > 6:
            return {"error": "Maximum 6 stock symbols can be analyzed"}

        stock_data = {}
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

        # Her sembol için veri toplama
        for symbol in symbols:
            try:
                data_response = None

                if period.lower() == "intraday":
                    data_response = await get_intraday_data(
                        symbols=symbol, interval="60min"
                    )
                elif period.lower() == "daily":
                    data_response = await get_eod_data(symbols=symbol)
                else:
                    # Marketstack doesn't have weekly/monthly endpoints, use daily data
                    data_response = await get_eod_data(symbols=symbol)

                if "error" in data_response or "Error Message" in data_response:
                    continue

                # Marketstack data structure
                if "data" not in data_response:
                    continue

                # DataFrame'e çevir
                raw_data = data_response["data"]
                if not raw_data:
                    continue

                # Convert to DataFrame
                df = pd.DataFrame(raw_data)
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)

                # Kolon isimlerini standardize et
                column_mapping = {
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "volume": "volume",
                }

                # Rename columns to lowercase for consistency
                df.columns = [col.lower() for col in df.columns]

                # Ensure we have the required columns
                required_cols = ["open", "high", "low", "close"]
                if not all(col in df.columns for col in required_cols):
                    continue

                # Numeric'e çevir ve sırala
                for col in required_cols + (
                    ["volume"] if "volume" in df.columns else []
                ):
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.sort_index()

                # Tarih filtreleme
                if time_range_days and time_range_days > 0:
                    df = df.tail(time_range_days)

                # Moving Average hesapla
                if include_ma and len(df) >= ma_period:
                    df[f"MA{ma_period}"] = df["close"].rolling(window=ma_period).mean()

                stock_data[symbol] = df

            except Exception as e:
                chart_logger.error(f"Error processing {symbol}: {e}")
                continue

        if not stock_data:
            return {"error": "No data could be retrieved for any symbol"}

        # Grafik oluşturma
        fig = None
        symbols_list = list(stock_data.keys())

        if subplot_layout == "quantstart" and len(symbols_list) >= 5:
            fig = make_subplots(
                rows=3,
                cols=2,
                specs=[
                    [{"colspan": 2, "secondary_y": True}, None],
                    [{"secondary_y": True}, {"secondary_y": True}],
                    [{"secondary_y": True}, {"secondary_y": True}],
                ],
                subplot_titles=symbols_list,
                x_title="Date",
                y_title="OHLC",
            )

            plot_symbols = [symbols_list[0], symbols_list[0]] + symbols_list[1:5]

            for i, symbol in enumerate(plot_symbols):
                # QuantStart exact logic
                if i == 1:
                    row = 1
                    col = 1
                else:
                    row = (i // 2) + 1
                    col = (i % 2) + 1

                df = stock_data[symbol]

                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        name="OHLC",
                    ),
                    row=row,
                    col=col,
                )

                if include_volume and "volume" in df.columns:
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df["volume"],
                            opacity=0.1,
                            marker=dict(color="blue"),
                            name="volume",
                        ),
                        row=row,
                        col=col,
                        secondary_y=True,
                    )

                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            line=dict(color="black", width=1),
                            name=f"{ma_period} day MA",
                            yaxis="y2",
                        ),
                        row=row,
                        col=col,
                        secondary_y=False,
                    )

                fig.layout.yaxis2.showgrid = False

            fig.update_layout(
                showlegend=False,
                title_text=f"OHLC data for {', '.join(symbols_list)}",
                title_xref="paper",
                title_x=0.5,
                title_xanchor="center",
            )
            fig.update_xaxes(rangeslider_visible=False)

        elif subplot_layout == "single" and len(symbols_list) == 1:
            symbol = symbols_list[0]
            df = stock_data[symbol]

            if include_volume and "volume" in df.columns:
                fig = make_subplots(
                    rows=2,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    subplot_titles=(f"{symbol} {chart_type.title()}", "Volume"),
                    row_width=[0.7, 0.3],
                )

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"],
                            high=df["high"],
                            low=df["low"],
                            close=df["close"],
                            name=f"{symbol} OHLC",
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        ),
                        row=1,
                        col=1,
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0], width=2),
                        ),
                        row=1,
                        col=1,
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0]),
                        ),
                        row=1,
                        col=1,
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"MA({ma_period})",
                            line=dict(color="orange", width=2, dash="dash"),
                        ),
                        row=1,
                        col=1,
                    )

                # Volume
                fig.add_trace(
                    go.Bar(
                        x=df.index,
                        y=df["volume"],
                        name="Volume",
                        marker=dict(color="rgba(158,202,225,0.6)"),
                    ),
                    row=2,
                    col=1,
                )

            else:
                fig = go.Figure()

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"],
                            high=df["high"],
                            low=df["low"],
                            close=df["close"],
                            name=f"{symbol} OHLC",
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        )
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0], width=2),
                        )
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0]),
                        )
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"MA({ma_period})",
                            line=dict(color="orange", width=2, dash="dash"),
                        )
                    )

            fig.update_layout(
                title=f"{symbol} Stock Analysis",
                template="plotly_white",
                height=(600 if (include_volume and "volume" in df.columns) else 400),
                showlegend=True,
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                hovermode="x unified",
            )

        # GRID LAYOUT
        elif subplot_layout == "grid":
            rows = (len(symbols_list) + 1) // 2
            cols = 2 if len(symbols_list) > 1 else 1

            specs = []
            for _ in range(rows):
                row_specs = []
                for _ in range(cols):
                    row_specs.append({"secondary_y": True} if include_volume else {})
                specs.append(row_specs)

            fig = make_subplots(
                rows=rows,
                cols=cols,
                specs=specs,
                subplot_titles=symbols_list,
                vertical_spacing=0.08,
                horizontal_spacing=0.05,
            )

            for i, symbol in enumerate(symbols_list):
                row = (i // cols) + 1
                col = (i % cols) + 1
                df = stock_data[symbol]
                color = colors[i % len(colors)]

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"],
                            high=df["high"],
                            low=df["low"],
                            close=df["close"],
                            name=f"{symbol}",
                            showlegend=False,
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        ),
                        row=row,
                        col=col,
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            name=f"{symbol}",
                            line=dict(color=color, width=2),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol}",
                            line=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"{symbol} MA",
                            line=dict(color="orange", width=1, dash="dash"),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                    )

                # Volume
                if include_volume and "volume" in df.columns:
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df["volume"],
                            name=f"{symbol} Volume",
                            opacity=0.3,
                            marker_color=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                        secondary_y=True,
                    )

            fig.update_layout(
                title="Multi-Stock Analysis (Grid Layout)",
                height=300 * rows,
                showlegend=False,
                template="plotly_white",
            )

        else:
            specs = [
                [{"secondary_y": True}] if include_volume else [{}]
                for _ in symbols_list
            ]

            fig = make_subplots(
                rows=len(symbols_list),
                cols=1,
                specs=specs,
                subplot_titles=symbols_list,
                vertical_spacing=0.05,
            )

            for i, symbol in enumerate(symbols_list):
                row = i + 1
                df = stock_data[symbol]
                color = colors[i % len(colors)]

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"],
                            high=df["high"],
                            low=df["low"],
                            close=df["close"],
                            name=f"{symbol}",
                            showlegend=False,
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        ),
                        row=row,
                        col=1,
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            name=f"{symbol}",
                            line=dict(color=color, width=2),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["close"],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol}",
                            line=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"{symbol} MA",
                            line=dict(color="orange", width=1, dash="dash"),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )

                # Volume
                if include_volume and "volume" in df.columns:
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df["volume"],
                            name=f"{symbol} Volume",
                            opacity=0.3,
                            marker_color=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                        secondary_y=True,
                    )

            fig.update_layout(
                title="Multi-Stock Analysis (Vertical Layout)",
                height=400 * len(symbols_list),
                showlegend=False,
                template="plotly_white",
            )

        if fig is None:
            return {"error": "Chart could not be created"}

        # Ortak layout ayarları
        fig.update_xaxes(rangeslider_visible=False)

        # Range selector ekle (sadece single layout için)
        if subplot_layout == "single":
            fig.update_xaxes(
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(
                                count=1, label="1M", step="month", stepmode="backward"
                            ),
                            dict(
                                count=3, label="3M", step="month", stepmode="backward"
                            ),
                            dict(
                                count=6, label="6M", step="month", stepmode="backward"
                            ),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(step="all"),
                        ]
                    )
                )
            )

        # HTML'e çevir
        chart_logger.info("🔄 Converting chart to HTML...")
        chart_html = fig.to_html(
            include_plotlyjs="cdn",
            div_id=f"stock_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config={"displayModeBar": True, "responsive": True},
        )

        chart_logger.info(f"✅ HTML generated successfully - Length: {len(chart_html)}")
        chart_logger.info(f"  HTML preview: {chart_html[:300]}...")

        chart_id = str(uuid.uuid4())
        chart_file = CHARTS_DIR / f"{chart_id}.html"

        # Create chart data with metadata - same structure as images
        chart_data = {
            "filename": f"{chart_id}.html",
            "data": chart_html,
            "reference": chart_id,
            "type": "text/html",
            "symbols": symbols_list,
            "chart_type": chart_type,
            "period": period,
            "time_range_days": time_range_days,
            "created_at": datetime.now().isoformat(),
            "file_path": str(chart_file),
        }

        chart_logger.info("📊 Setting chart data to global storage...")
        set_chart_data(chart_data)

        chart_logger.info(f"💾 Saving chart to file: {chart_file}")
        try:
            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(chart_html)
            chart_logger.info(f"✅ Chart saved successfully to {chart_file}")
        except Exception as e:
            chart_logger.error(f"❌ Error saving chart to file: {e}")

        chart_logger.info(f"🎯 Chart operation completed - ID: {chart_id}")
        return {
            "message": f"✅ {len(symbols_list)} stock {chart_type} chart created successfully ({subplot_layout} layout). Chart is displayed above this response for your analysis."
        }

    except Exception as e:
        return {"error": f"Stock chart creation error: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
