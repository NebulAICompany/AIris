import httpx
import sys
from pathlib import Path
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.shared.constants import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL
from backend.utils.news import get_aggregated_financial_news, NewsResponse, FINANCIAL_NEWS_SOURCES, NewsSource

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


@mcp.tool()
async def get_financial_news(
    max_per_source: int = 20
) -> Dict[str, Any]:
    """
    Get aggregated financial news from multiple sources with intelligent LLM-based clustering.
    
    This function fetches news from multiple financial sources, uses advanced LLM analysis
    to understand story relationships and groups articles by underlying financial events,
    presenting them in a unified format similar to Perplexity.ai's discover page.

    Optional:
        max_per_source (int): Maximum articles to fetch from each source (default: 20)

    Returns:
        dict: Aggregated news response containing:
            - clustered_articles: News stories grouped by LLM analysis with unified titles/descriptions
            - single_articles: Stories appearing in only one source  
            - total_clusters: Number of story clusters found
            - total_articles: Total number of articles processed
            - sources_info: Information about news sources used
            - clustering_method: "llm-based" for intelligent story understanding
            - content_analysis: LLM's overall analysis of the news landscape
    """
    
    try:
        # Get the aggregated news
        response = await get_aggregated_financial_news()
        
        # Convert response to dict and add source information
        result = response.dict()
        
        # TEMPORARILY: Filter to show only clustered articles
        result["single_articles"] = []  # Hide single articles temporarily
        result["display_mode"] = "clustered_only"
        result["feature"] = "multi_source_clustering_only"
        
        # Add information about sources and clustering method
        result["sources_info"] = {
            "total_sources": len(FINANCIAL_NEWS_SOURCES),
            "sources": [{"name": source.name, "language": source.language} 
                       for source in FINANCIAL_NEWS_SOURCES]
        }
        result["clustering_method"] = "llm-based"
        
        # Include content quality statistics
        print(f"Content quality: {result.get('articles_with_summary', 0)} with summaries, {result.get('articles_without_summary', 0)} titles only ({result.get('summary_coverage_percentage', 0):.1f}% coverage)")
        
        return result
        
    except Exception as e:
        return {
            "error": f"Failed to fetch financial news: {str(e)}",
            "clustered_articles": [],
            "single_articles": [],
            "total_clusters": 0,
            "total_articles": 0,
            "sources_info": {
                "total_sources": len(FINANCIAL_NEWS_SOURCES),
                "sources": [{"name": source.name, "language": source.language} 
                           for source in FINANCIAL_NEWS_SOURCES]
            }
        }


@mcp.tool()
async def get_financial_news_sources() -> Dict[str, Any]:
    """
    Get information about all configured financial news sources.
    
    Returns:
        dict: Information about news sources including names, URLs, and languages
    """
    
    sources_info = []
    for source in FINANCIAL_NEWS_SOURCES:
        sources_info.append({
            "name": source.name,
            "rss_url": source.rss_url,
            "language": source.language
        })
    
    return {
        "total_sources": len(FINANCIAL_NEWS_SOURCES),
        "sources": sources_info
    }


if __name__ == "__main__":
    mcp.run(transport='stdio')
