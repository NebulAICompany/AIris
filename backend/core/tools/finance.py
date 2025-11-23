import httpx
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any
from langchain_core.tools import tool
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import uuid

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
    return make_request("eod", params)


@tool
def get_eod_latest(
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
    return make_request("eod/latest", params)


@tool
def get_eod_date(
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
    return make_request(f"eod/{date}", params)


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
    return make_request("intraday", params)


@tool
def get_intraday_latest(
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
    return make_request("intraday/latest", params)


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
# BONDS METHODS
# ============================================================================


@tool
def get_bond_list(
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
    return make_request("bondlist", params)


@tool
def get_bond_info(
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
    return make_request("bond", params)


# ============================================================================
# ETF HOLDINGS METHODS
# ============================================================================


@tool
def get_etf_list(
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
    return make_request("etflist", params)


@tool
def get_etf_holdings(
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
    return make_request("etfholdings", params)


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
# HIGHER PLAN METHODS (COMMENTED OUT - NOT AVAILABLE FOR BASIC PLAN)
# ============================================================================

# ============================================================================
# PROFESSIONAL PLAN METHODS (403 Forbidden for Free/Basic Plans)
# ============================================================================

# @tool
# def get_realtime_stock_price(
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
#     return make_request("stockprice", params)


# @tool
# def get_commodity_prices(
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
#     return make_request("commodities", params)


# @tool
# def get_commodities_history(
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
#     return make_request("commoditieshistory", params)


# ============================================================================
# BUSINESS PLAN METHODS (403 Forbidden for Free/Basic/Professional Plans)
# ============================================================================

# @tool
# def get_company_ratings(
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
#     return make_request("companyratings", params)


# @tool
# def find_cik_by_company_name_edgar(
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
#     return make_request("cik_code", params)


# @tool
# def find_company_name_by_cik_edgar(
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
#     return make_request("company_name", params)


# @tool
# def get_company_submissions_edgar(
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
#     return make_request("submissions", params)


# @tool
# def get_company_facts_edgar(
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
#     return make_request("company_facts", params)


# @tool
# def get_company_concepts_accounts_payable(
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
#     return make_request("concept/accounts_payable", params)


# @tool
# def get_frames_accounts_payable(
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
#     return make_request(f"frames/accounts_payable/{units}", params)


# ============================================================================
# COMPANY DATA METHODS (Legacy - Business Plan Required)
# ============================================================================

# @tool
# def find_cik_by_company_name(
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
#     return make_request("cik_code", params)


# @tool
# def find_company_name_by_cik(
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
#     return make_request("company_name", params)


# @tool
# def get_company_submissions(
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
#     return make_request(f"company_submissions/{cik}/submissions", params)


# @tool
# def get_company_facts(
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
#     return make_request(f"company_facts/{cik}", params)


# @tool
# def get_company_concepts(
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
#     return make_request(f"company_concepts/{cik}", params)


# @tool
# def get_frames(
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
#     return make_request("frames", params)


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


# ============================================================================
# MODERN STOCK CHART FUNCTION
# ============================================================================


@tool
def create_stock_chart(
    symbols: list,
    period: str = "daily",
    chart_type: str = "candlestick",
    time_range_days: int = 180,
    include_volume: bool = True,
    technical_indicators: list = None,
    layout_style: str = "professional",
):
    """
    Create modern and professional stock charts with advanced technical analysis.

    Required:
        symbols (list): List of stock symbols (e.g., ["AAPL", "MSFT"])

    Optional:
        period (str): "daily" or "intraday" (default: "daily")
        chart_type (str): "candlestick", "ohlc", "line", "area" (default: "candlestick")
        time_range_days (int): Days of historical data (default: 60)
        include_volume (bool): Show volume chart (default: True)
        technical_indicators (list): ["sma", "ema", "bollinger", "rsi", "macd"] (default: ["sma"])
        layout_style (str): "professional", "dark", "minimal" (default: "professional")

    Returns:
        dict: Success message with chart creation details
    """
    try:
        # Input validation and defaults
        if not symbols or len(symbols) == 0:
            return {"error": "At least one stock symbol is required"}

        if len(symbols) > 4:
            return {"error": "Maximum 4 symbols allowed for optimal visualization"}

        # Set default technical indicators if none provided
        if technical_indicators is None:
            technical_indicators = ["sma"]

        # Ensure charts directory exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        # Modern color palette
        COLORS = {
            "professional": {
                "primary": ["#2E86C1", "#E74C3C", "#F39C12", "#8E44AD"],
                "secondary": ["#5DADE2", "#EC7063", "#F7C71A", "#BB8FCE"],
                "background": "#FFFFFF",
                "grid": "#F8F9FA",
                "text": "#2C3E50",
                "candlestick_up": "#00C851",
                "candlestick_down": "#FF4444",
                "volume": "rgba(70, 130, 180, 0.5)",
            },
            "dark": {
                "primary": ["#00D4AA", "#FF6B6B", "#4ECDC4", "#45B7D1"],
                "secondary": ["#96CEB4", "#FECA57", "#FF9FF3", "#54A0FF"],
                "background": "#1E1E1E",
                "grid": "#2D2D2D",
                "text": "#FFFFFF",
                "candlestick_up": "#00D4AA",
                "candlestick_down": "#FF6B6B",
                "volume": "rgba(0, 212, 170, 0.3)",
            },
            "minimal": {
                "primary": ["#6C5CE7", "#00B894", "#FDCB6E", "#E17055"],
                "secondary": ["#A29BFE", "#00CEC9", "#FDCB6E", "#FD79A8"],
                "background": "#FDFDFD",
                "grid": "#F1F2F6",
                "text": "#2D3436",
                "candlestick_up": "#00B894",
                "candlestick_down": "#E17055",
                "volume": "rgba(108, 92, 231, 0.4)",
            },
        }

        color_scheme = COLORS.get(layout_style, COLORS["professional"])

        # Fetch data for all symbols
        stock_data = {}
        failed_symbols = []

        for symbol in symbols:
            try:
                # Fetch market data with increased limits
                if period.lower() == "intraday":
                    response = get_intraday_data(
                        symbols=symbol,
                        interval="1hour",
                        limit=min(time_range_days * 12, 1000),
                    )
                else:
                    response = get_eod_data(
                        symbols=symbol, limit=min(max(time_range_days, 250), 1000)
                    )

                if (
                    "error" in response
                    or "data" not in response
                    or not response["data"]
                ):
                    failed_symbols.append(symbol)
                    continue

                # Process data
                df = pd.DataFrame(response["data"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()

                # Ensure numeric columns
                numeric_cols = ["open", "high", "low", "close", "volume"]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                # Validate required data
                required_cols = ["open", "high", "low", "close"]
                if not all(col in df.columns for col in required_cols):
                    failed_symbols.append(symbol)
                    continue

                # Drop rows with missing OHLC data
                df = df.dropna(subset=required_cols)

                if len(df) == 0:
                    failed_symbols.append(symbol)
                    continue

                # Limit data to requested time range
                if time_range_days > 0:
                    df = df.tail(time_range_days)

                # Calculate technical indicators
                if "sma" in technical_indicators:
                    df["SMA_20"] = calculate_sma(df["close"], 20)
                    df["SMA_50"] = calculate_sma(df["close"], 50)

                if "ema" in technical_indicators:
                    df["EMA_12"] = calculate_ema(df["close"], 12)
                    df["EMA_26"] = calculate_ema(df["close"], 26)

                if "bollinger" in technical_indicators:
                    df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = (
                        calculate_bollinger_bands(df["close"])
                    )

                if "rsi" in technical_indicators:
                    df["RSI"] = calculate_rsi(df["close"])

                if "macd" in technical_indicators:
                    df["MACD"], df["MACD_Signal"], df["MACD_Histogram"] = (
                        calculate_macd(df["close"])
                    )

                stock_data[symbol] = df

            except Exception as e:
                failed_symbols.append(symbol)
                continue

        if not stock_data:
            return {
                "error": f"Could not retrieve data for any symbols. Failed: {', '.join(failed_symbols)}"
            }

        successful_symbols = list(stock_data.keys())

        # Create chart layout
        subplot_count = len(successful_symbols)
        has_rsi = "rsi" in technical_indicators
        has_macd = "macd" in technical_indicators
        has_volume = include_volume and any(
            "volume" in df.columns for df in stock_data.values()
        )

        # Calculate subplot rows
        extra_rows = 0
        if has_volume:
            extra_rows += 1
        if has_rsi:
            extra_rows += 1
        if has_macd:
            extra_rows += 1

        total_rows = subplot_count + extra_rows
        row_heights = []

        # Main price charts get more height
        for _ in range(subplot_count):
            row_heights.append(
                0.65 / subplot_count if extra_rows > 0 else 1.0 / subplot_count
            )

        # Technical indicator rows get optimized heights
        if has_volume:
            row_heights.append(0.18 if extra_rows > 1 else 0.4)
        if has_rsi:
            row_heights.append(0.085 if extra_rows > 1 else 0.3)
        if has_macd:
            row_heights.append(0.085 if extra_rows > 1 else 0.3)

        # Create subplot specifications
        specs = [[{"secondary_y": False}] for _ in range(total_rows)]
        subplot_titles = []

        for symbol in successful_symbols:
            latest_price = stock_data[symbol]["close"].iloc[-1]
            price_change = (
                stock_data[symbol]["close"].iloc[-1]
                - stock_data[symbol]["close"].iloc[-2]
                if len(stock_data[symbol]) > 1
                else 0
            )
            change_pct = (
                (price_change / stock_data[symbol]["close"].iloc[-2] * 100)
                if len(stock_data[symbol]) > 1
                and stock_data[symbol]["close"].iloc[-2] != 0
                else 0
            )

            change_symbol = "+" if price_change >= 0 else ""
            subplot_titles.append(
                f"{symbol} - ${latest_price:.2f} ({change_symbol}{change_pct:.2f}%)"
            )

        if has_volume:
            subplot_titles.append("Volume")
        if has_rsi:
            subplot_titles.append("RSI")
        if has_macd:
            subplot_titles.append("MACD")

        # Create the figure
        fig = make_subplots(
            rows=total_rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.015,  # Reduced spacing for more chart area
            subplot_titles=subplot_titles,
            specs=specs,
            row_heights=row_heights,
        )

        # Plot main price charts
        for i, symbol in enumerate(successful_symbols):
            df = stock_data[symbol]
            row = i + 1
            color = color_scheme["primary"][i % len(color_scheme["primary"])]

            # Main price chart
            if chart_type == "candlestick":
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        name=f"{symbol}",
                        increasing=dict(
                            line=dict(color=color_scheme["candlestick_up"], width=2)
                        ),
                        decreasing=dict(
                            line=dict(color=color_scheme["candlestick_down"], width=2)
                        ),
                        showlegend=True,
                    ),
                    row=row,
                    col=1,
                )
            elif chart_type == "ohlc":
                fig.add_trace(
                    go.Ohlc(
                        x=df.index,
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        name=f"{symbol}",
                        increasing=dict(
                            line=dict(color=color_scheme["candlestick_up"], width=2)
                        ),
                        decreasing=dict(
                            line=dict(color=color_scheme["candlestick_down"], width=2)
                        ),
                        showlegend=True,
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
                        line=dict(color=color, width=3),
                        showlegend=True,
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
                        line=dict(color=color, width=2),
                        fillcolor=f"rgba{tuple(list(bytes.fromhex(color.lstrip('#'))) + [0.1])}",
                        showlegend=True,
                    ),
                    row=row,
                    col=1,
                )

            # Add technical indicators
            if "sma" in technical_indicators:
                if "SMA_20" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["SMA_20"],
                            mode="lines",
                            name=f"{symbol} SMA(20)",
                            line=dict(
                                color="#FFA500",  # Orange - more visible
                                width=3,
                                dash="dash",
                            ),
                            showlegend=True,
                            opacity=0.9,
                        ),
                        row=row,
                        col=1,
                    )

                if "SMA_50" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["SMA_50"],
                            mode="lines",
                            name=f"{symbol} SMA(50)",
                            line=dict(
                                color="#9932CC",  # Purple - more visible
                                width=3,
                                dash="dot",
                            ),
                            showlegend=True,
                            opacity=0.9,
                        ),
                        row=row,
                        col=1,
                    )

            if "ema" in technical_indicators:
                if "EMA_12" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["EMA_12"],
                            mode="lines",
                            name=f"{symbol} EMA(12)",
                            line=dict(
                                color=color_scheme["primary"][
                                    i % len(color_scheme["primary"])
                                ],
                                width=1.5,
                                dash="dash",
                            ),
                            opacity=0.8,
                            showlegend=True,
                        ),
                        row=row,
                        col=1,
                    )

            if "bollinger" in technical_indicators:
                if all(
                    col in df.columns for col in ["BB_Upper", "BB_Middle", "BB_Lower"]
                ):
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["BB_Upper"],
                            mode="lines",
                            name=f"{symbol} BB Upper",
                            line=dict(color="rgba(128,128,128,0.5)", width=1),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["BB_Lower"],
                            mode="lines",
                            name=f"{symbol} BB Lower",
                            line=dict(color="rgba(128,128,128,0.5)", width=1),
                            fill="tonexty",
                            fillcolor="rgba(128,128,128,0.1)",
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )

        # Add volume chart with improved visibility
        current_row = len(successful_symbols) + 1
        if has_volume:
            for i, symbol in enumerate(successful_symbols):
                df = stock_data[symbol]
                if "volume" in df.columns:
                    # Color volume bars based on price movement
                    colors = []
                    for j in range(len(df)):
                        if j > 0:
                            if df["close"].iloc[j] >= df["close"].iloc[j - 1]:
                                colors.append(
                                    "rgba(0, 200, 81, 0.7)"
                                )  # Green for up days
                            else:
                                colors.append(
                                    "rgba(255, 68, 68, 0.7)"
                                )  # Red for down days
                        else:
                            colors.append("rgba(100, 149, 237, 0.7)")  # Default blue

                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df["volume"],
                            name=f"{symbol} Volume",
                            marker_color=colors,
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )
            current_row += 1

        # Add RSI chart
        if has_rsi:
            for i, symbol in enumerate(successful_symbols):
                df = stock_data[symbol]
                if "RSI" in df.columns:
                    color = color_scheme["primary"][i % len(color_scheme["primary"])]
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["RSI"],
                            mode="lines",
                            name=f"{symbol} RSI",
                            line=dict(color=color, width=3),  # Increased width
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

            # Add RSI reference lines
            fig.add_hline(
                y=70,
                line_dash="dash",
                line_color="red",
                opacity=0.5,
                row=current_row,
                col=1,
            )
            fig.add_hline(
                y=30,
                line_dash="dash",
                line_color="green",
                opacity=0.5,
                row=current_row,
                col=1,
            )
            fig.add_hline(
                y=50,
                line_dash="dot",
                line_color="gray",
                opacity=0.3,
                row=current_row,
                col=1,
            )

            current_row += 1

        # Add MACD chart
        if has_macd:
            for i, symbol in enumerate(successful_symbols):
                df = stock_data[symbol]
                if all(
                    col in df.columns
                    for col in ["MACD", "MACD_Signal", "MACD_Histogram"]
                ):
                    color = color_scheme["primary"][i % len(color_scheme["primary"])]

                    # MACD line
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["MACD"],
                            mode="lines",
                            name=f"{symbol} MACD",
                            line=dict(color=color, width=3),  # Increased width
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

                    # Signal line
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["MACD_Signal"],
                            mode="lines",
                            name=f"{symbol} Signal",
                            line=dict(
                                color=color_scheme["secondary"][
                                    i % len(color_scheme["secondary"])
                                ],
                                width=3,  # Increased width
                            ),
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

                    # Histogram
                    colors_hist = [
                        "green" if x >= 0 else "red" for x in df["MACD_Histogram"]
                    ]
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df["MACD_Histogram"],
                            name=f"{symbol} Histogram",
                            marker_color=colors_hist,
                            opacity=0.6,
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

        # Update layout with modern styling
        fig.update_layout(
            title=dict(
                text=f"Professional Stock Analysis: {', '.join(successful_symbols)}",
                x=0.5,
                font=dict(
                    size=24, color=color_scheme["text"], family="Arial, sans-serif"
                ),
            ),
            template="plotly_white" if layout_style != "dark" else "plotly_dark",
            plot_bgcolor=color_scheme["background"],
            paper_bgcolor=color_scheme["background"],
            font=dict(color=color_scheme["text"], family="Arial, sans-serif"),
            height=300
            + (450 * len(successful_symbols))
            + (200 * extra_rows),  # Increased height
            margin=dict(l=60, r=60, t=120, b=100),  # Optimized margins
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.05,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1,
            ),
            xaxis=dict(
                rangeslider=dict(visible=False),
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(count=7, label="7D", step="day", stepmode="backward"),
                            dict(
                                count=30, label="30D", step="day", stepmode="backward"
                            ),
                            dict(
                                count=60, label="60D", step="day", stepmode="backward"
                            ),
                            dict(
                                count=90, label="90D", step="day", stepmode="backward"
                            ),
                            dict(step="all", label="ALL"),
                        ]
                    ),
                    bgcolor=color_scheme["grid"],
                    activecolor=color_scheme["primary"][0],
                ),
            ),
        )

        # Style all subplots
        fig.update_xaxes(
            gridcolor=color_scheme["grid"],
            showline=True,
            linecolor=color_scheme["grid"],
            mirror=True,
        )
        fig.update_yaxes(
            gridcolor=color_scheme["grid"],
            showline=True,
            linecolor=color_scheme["grid"],
            mirror=True,
        )

        # Generate unique chart ID and save
        chart_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Convert to HTML with modern configuration
        chart_html = fig.to_html(
            include_plotlyjs="cdn",
            div_id=f"professional_stock_chart_{timestamp}",
            config={
                "displayModeBar": True,
                "responsive": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": [
                    "drawline",
                    "drawopenpath",
                    "drawclosedpath",
                    "drawcircle",
                    "drawrect",
                    "eraseshape",
                ],
                "modeBarButtonsToRemove": ["pan2d", "lasso2d"],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": f"stock_chart_{timestamp}",
                    "height": 800,
                    "width": 1200,
                    "scale": 2,
                },
            },
        )

        # Save chart file
        chart_file = CHARTS_DIR / f"{chart_id}.html"

        # Create chart metadata
        chart_data = {
            "filename": f"{chart_id}.html",
            "data": chart_html,
            "reference": chart_id,
            "type": "text/html",
            "symbols": successful_symbols,
            "chart_type": chart_type,
            "period": period,
            "time_range_days": time_range_days,
            "technical_indicators": technical_indicators,
            "layout_style": layout_style,
            "created_at": datetime.now().isoformat(),
            "file_path": str(chart_file),
            "data_points": sum(len(df) for df in stock_data.values()),
            "failed_symbols": failed_symbols,
        }

        # Save chart data and file
        set_chart_data(chart_data)

        try:
            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(chart_html)
        except Exception as e:
            pass  # Silent fail for file writing issues

        success_message = (
            f"Chart created: {', '.join(successful_symbols)} | {chart_type.title()}"
        )

        if failed_symbols:
            success_message += f" | Failed: {', '.join(failed_symbols)}"

        return {"message": success_message}

    except Exception as e:
        return {"error": f"Chart creation failed: {str(e)}"}
