from agents import Agent
from backend.core.prompts import finance_agent_prompt, office_agent_prompt, news_summarization_prompt, tcmb_data_agent_prompt
from .office import *
from .tcmb_data import get_tcmb_subcategories, get_tcmb_series, get_tcmb_data
from .api import time_now
from .finance import (
    get_eod_data,
    get_eod_latest,
    get_eod_date,
    get_intraday_data,
    get_intraday_latest,
    get_exchanges,
    get_exchange_info,
    get_currencies,
    get_timezones,
    get_bond_list,
    get_bond_info,
    get_etf_list,
    get_etf_holdings,
    get_splits_data,
    get_dividends_data,
    get_index_list,
    get_index_info,
    get_tickers_list,
    get_ticker_info_detailed,
    create_stock_chart,
)
from backend.shared.constants import OPENAI_MODEL

office_tools = [
    create_excel_file,
    create_word_document,
    create_powerpoint_presentation,
    add_powerpoint_slide,
    modify_word_content,
    modify_excel_cells,
    create_excel_charts,
]

tcmb_tools = [
    time_now,
    get_tcmb_subcategories,
    get_tcmb_series,
    get_tcmb_data,
]

finance_tools = [
    get_eod_data,
    get_eod_latest,
    get_eod_date,
    get_intraday_data,
    get_intraday_latest,
    get_exchanges,
    get_exchange_info,
    get_currencies,
    get_timezones,
    get_bond_list,
    get_bond_info,
    get_etf_list,
    get_etf_holdings,
    get_splits_data,
    get_dividends_data,
    get_index_list,
    get_index_info,
    get_tickers_list,
    get_ticker_info_detailed,
    create_stock_chart,
]

finance_agent = Agent(
    name="Finance Agent",
    instructions=finance_agent_prompt,
    model=OPENAI_MODEL,
    tools=finance_tools,
)

office_agent = Agent(
    name="office_agent",
    instructions=office_agent_prompt,
    model=OPENAI_MODEL,
    tools=[
        *office_tools,
    ],
)

news_summarization_agent = Agent(
    name="Financial News Summarization Agent",
    instructions=news_summarization_prompt,
    tools=[],  # This agent uses only LLM capabilities, no external tools
)

tcmb_data_agent = Agent(
    name="TCMB Data Agent",
    instructions=tcmb_data_agent_prompt,
    model=OPENAI_MODEL,
    tools=tcmb_tools,
)

office_agent_tool = office_agent.as_tool(
    tool_name="office_operations",
    tool_description="""Use this tool for Microsoft Office operations including:
        - Creating Excel workbooks from structured data
        - Generating Word documents with custom content
        - Document processing and format conversion
        - Any task requiring Word or Excel functionality""",
)

finance_agent_tool = finance_agent.as_tool(
    tool_name="finance_agent",
    tool_description="""Use this tool for comprehensive financial data analysis including:
    - Real-time stock quotes and company information
    - Historical price data (intraday, daily, weekly, monthly)
    - Technical analysis with moving averages and volume indicators
    - Professional stock chart creation (candlestick, line, area)
    - Multi-stock comparison charts with multiple layouts
    - Market trend analysis and volatility assessment
    - Marketstack API integration for market data
    - Any financial data query requiring data retrieval or visualization""",
)

news_summarization_tool = news_summarization_agent.as_tool(
    tool_name="financial_news_summarization",
    tool_description="""Use this tool for creating unified summaries from multiple financial news articles covering the same story:
    - Combine titles and descriptions from multiple news sources
    - Create concise, unified titles for clustered news stories
    - Generate comprehensive summaries that synthesize information from all sources
    - Maintain objectivity and financial accuracy
    - Format output as JSON with unified_title and unified_description fields
    - Best used when you have 2+ articles about the same financial event/story""",
)

tcmb_data_agent_tool = tcmb_data_agent.as_tool(
    tool_name="tcmb_economic_data",
    tool_description=f"""Use this tool for comprehensive Turkish Central Bank (TCMB) economic data retrieval and analysis:
    - Access TCMB's EVDS (Electronic Data Delivery System) database
    - Retrieve economic indicators, exchange rates, interest rates, inflation data
    - Access balance of payments, reserves, money supply statistics
    - Get banking sector data, credit statistics, financial surveys
    - Fetch price indices, consumer/business tendency surveys
    - Access labor force, production, trade, and many other economics statistics
    
    The agent will:
    1. Identify relevant main categories for your query
    2. Explore subcategories to find specific data groups
    3. Select appropriate data series (max 10 series)
    4. Retrieve time series data for specified date ranges
    5. Provide analysis and interpretation of the economic data
    
    Best for queries about Turkish economic indicators, monetary policy data, financial statistics, and macroeconomic trends.""",
)
