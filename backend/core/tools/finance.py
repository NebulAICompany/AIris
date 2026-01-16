import httpx
import sys
import json
import time
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
