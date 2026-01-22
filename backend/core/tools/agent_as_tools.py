from langchain_core.tools import tool
from langchain.agents import create_agent
from backend.core.prompts import (
    finance_agent_prompt,
    office_agent_prompt,
    news_summarization_prompt,
    plotting_prompt,
    tcmb_data_agent_prompt,
)
from langchain.agents.middleware import ToolCallLimitMiddleware
from .office import *
from .tcmb_data import get_tcmb_subcategories, get_tcmb_series, get_tcmb_data
from .api import time_now
from .finance import (
    get_eod_data,
    get_intraday_data,
    get_exchanges,
    get_exchange_info,
    get_currencies,
    get_timezones,
    get_splits_data,
    get_dividends_data,
    get_index_list,
    get_index_info,
    get_tickers_list,
    get_ticker_info_detailed,
)
from backend.shared.constants import OPENAI_MODEL
from backend.core.tools.plotting import (
    create_custom_chart_from_code,
    create_financial_stock_chart,
)

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
    get_intraday_data,
    get_exchanges,
    get_exchange_info,
    get_currencies,
    get_timezones,
    get_splits_data,
    get_dividends_data,
    get_index_list,
    get_index_info,
    get_tickers_list,
    get_ticker_info_detailed,
]

# Create subagents using create_agent
finance_agent = create_agent(
    model=OPENAI_MODEL,
    tools=finance_tools,
    system_prompt=finance_agent_prompt,
)

office_agent = create_agent(
    model=OPENAI_MODEL,
    tools=office_tools,
    system_prompt=office_agent_prompt,
)


plotting_agent = create_agent(
    model=OPENAI_MODEL,
    tools=[
        create_custom_chart_from_code,
        create_financial_stock_chart,
    ],
    system_prompt=plotting_prompt,
    middleware=[
        ToolCallLimitMiddleware(
            tool_name="create_custom_chart_from_code",
            run_limit=1,
            exit_behavior="continue",
        ),
        ToolCallLimitMiddleware(
            tool_name="create_financial_stock_chart",
            run_limit=1,
            exit_behavior="continue",
        ),
    ],
)

tcmb_data_agent = create_agent(
    model=OPENAI_MODEL,
    tools=tcmb_tools,
    system_prompt=tcmb_data_agent_prompt,
)

news_summarization_agent = create_agent(
    model="gpt-4o-mini",
    tools=[],
    system_prompt=news_summarization_prompt,
)


# Wrap subagents as tools for the main agent
@tool(
    "finance_agent",
    description="""Use this tool for comprehensive financial market data retrieval and analysis:
    
    **Data Retrieval:**
    - Real-time and historical stock price data (OHLCV)
    - Intraday data with multiple intervals (1min to 24hour)
    - End-of-day (EOD) data for long-term analysis
    - Company information and ticker details
    - Exchange rates, currencies, timezones, dividends, and splits
    - Market indexes and financial statistics
    
    **Analysis Capabilities:**
    - Market data analysis and interpretation
    - Financial data processing and aggregation
    - Multi-timeframe analysis
    - Marketstack API integration
    
    **IMPORTANT:** This agent retrieves and analyzes financial DATA only.
    For financial chart visualization, the data will be passed to the plotting_agent.
    
    Input: Natural language query about financial data retrieval or analysis.""",
)
async def call_finance_agent(query: str) -> str:
    """Call the finance specialist agent."""
    result = await finance_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


@tool(
    "office_operations",
    description="""Use this tool for Microsoft Office operations including:
    - Creating Excel workbooks from structured data
    - Generating Word documents with custom content
    - Creating PowerPoint presentations
    - Document processing and format conversion
    - Any task requiring Word, Excel, or PowerPoint functionality
    
    Input: Natural language request for Office document operations.""",
)
async def call_office_agent(query: str) -> str:
    """Call the office operations specialist agent."""
    result = await office_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


@tool(
    "plotting_agent",
    description="""Use this tool for ALL chart creation and data visualization needs:
    
    **TWO VISUALIZATION METHODS:**
    
    1. **Financial Stock Charts (create_financial_stock_chart):**
       USE FOR:
       - Stock market price charts with OHLC data
       - Candlestick, OHLC, line, and area charts
       - Technical indicators (SMA, EMA, Bollinger, RSI, MACD)
       - Volume analysis with subplots
       - Multi-stock comparison (up to 4 stocks)
       - Professional financial market visualizations
       - Interactive charts with range selectors
       
       Automatically fetches market data and creates professional financial charts.
    
    2. **Custom Charts from Code (create_custom_chart_from_code):**
       USE FOR:
       - Statistical plots (histograms, box plots, scatter plots)
       - Distribution analysis and correlations
       - Custom data visualizations with matplotlib/seaborn/plotly
       - Scientific charts and academic plots
       - Any non-financial custom visualization
       
       Executes Python code in a sandbox to create custom charts.
    
    **Supported Libraries:**
    - matplotlib, seaborn, plotly, pandas, numpy
    
    **Key Distinction:**
    - Financial stock charts → Use create_financial_stock_chart (no code needed)
    - Everything else → Use create_custom_chart_from_code (requires Python code)
    
    **Important:**
    - Charts are automatically displayed after creation
    - Do NOT add chart content to the answer
    - Focus on explaining insights and analysis
    
    Input: Natural language request describing the chart or visualization needed.""",
)
async def call_plotting_agent(query: str) -> str:
    """Call the plotting specialist agent."""
    result = await plotting_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


@tool(
    "tcmb_economic_data",
    description="""Use this tool for comprehensive Turkish Central Bank (TCMB) economic data retrieval and analysis:
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
    
    Best for queries about Turkish economic indicators, monetary policy data, financial statistics, and macroeconomic trends.
    
    Input: Natural language query about Turkish economic data.""",
)
async def call_tcmb_agent(query: str) -> str:
    """Call the TCMB economic data specialist agent."""
    result = await tcmb_data_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


@tool(
    "financial_news_summarization",
    description="""Use this tool for creating unified summaries from multiple financial news articles covering the same story:
    - Combine titles and descriptions from multiple news sources
    - Create concise, unified titles for clustered news stories
    - Generate comprehensive summaries that synthesize information from all sources
    - Maintain objectivity and financial accuracy
    - Format output as JSON with unified_title and unified_description fields
    - Best used when you have 2+ articles about the same financial event/story
    
    Input: Multiple news article titles and descriptions about the same story.""",
)
async def call_news_summarization_agent(query: str) -> str:
    """Call the financial news summarization specialist agent."""
    result = await news_summarization_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


# List of subagent tools for the main agent
main_agent_subagents = [
    call_finance_agent,
    call_office_agent,
    call_plotting_agent,
    call_tcmb_agent,
    call_news_summarization_agent,
]
