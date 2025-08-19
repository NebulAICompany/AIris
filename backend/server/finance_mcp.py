import httpx
import sys
from pathlib import Path
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.shared.constants import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL

mcp = FastMCP("alpha_vantage")
async def make_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Alpha Vantage API'sine async istek gönder"""
    params['apikey'] = ALPHA_VANTAGE_API_KEY

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_intraday_data(
        symbol: str,
        interval: str,
        outputsize: str = None,
        adjusted: bool = None,
        extended_hours: bool = None,
        month: str = None,
):
    """
    Fetch intraday OHLCV data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")
        interval (str): "1min" | "5min" | "15min" | "30min" | "60min"

    Optional:
        outputsize (str): "compact" or "full"
        adjusted (bool): True/False
        extended_hours (bool): True/False
        month (str): YYYY-MM format (e.g., "2009-01")

    Returns:
        dict: Intraday time series data with OHLCV values covering current and 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        **({"outputsize": outputsize} if outputsize else {}),
        **({"adjusted": str(adjusted).lower()} if adjusted is not None else {}),
        **({"extended_hours": str(extended_hours).lower()} if extended_hours is not None else {}),
        **({"month": month} if month else {}),
    }

    return await make_request(params)

@mcp.tool()
async def get_daily_data(
        symbol: str,
        outputsize: str = None,
):
    """
    Fetch daily OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Optional:
        outputsize (str): "compact" or "full"

    Returns:
        dict: Raw daily time series data with OHLCV values covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        **({"outputsize": outputsize} if outputsize else {}),
    }

    return await make_request(params)


@mcp.tool()
async def get_weekly_data(
        symbol: str,
):
    """
    Fetch weekly OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Weekly time series data with OHLCV values covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_WEEKLY",
        "symbol": symbol,
    }

    return await make_request(params)

@mcp.tool()
async def get_weekly_adjusted_data(
        symbol: str,
):
    """
    Fetch weekly adjusted OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Weekly adjusted time series data with OHLCV values, adjusted close, volume and dividend covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_WEEKLY_ADJUSTED",
        "symbol": symbol,
    }

    return await make_request(params)

@mcp.tool()
async def get_monthly_data(
        symbol: str,
):
    """
    Fetch monthly OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Monthly time series data with OHLCV values covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_MONTHLY",
        "symbol": symbol,
    }

    return await make_request(params)

@mcp.tool()
async def get_monthly_adjusted_data(
        symbol: str,
):
    """
    Fetch monthly adjusted OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Monthly adjusted time series data with OHLCV values, adjusted close, volume and dividend covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": symbol,
    }

    return await make_request(params)

@mcp.tool()
async def get_global_quote(
        symbol: str,
):
    """
    Fetch latest price and volume information for a ticker from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Latest price and volume information for the specified ticker
    """

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
    }

    return await make_request(params)


if __name__ == "__main__":
    mcp.run(transport='stdio')
