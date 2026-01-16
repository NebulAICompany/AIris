from langchain_core.tools import tool
from langchain.agents import create_agent
from backend.core.prompts import (
    finance_agent_prompt,
    office_agent_prompt,
    news_summarization_prompt,
    plotting_prompt,
    tcmb_data_agent_prompt,
)
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
from backend.core.tools.plotting import execute_code_and_save_image

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
        execute_code_and_save_image,
    ],
    system_prompt=plotting_prompt,
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
    description="""Use this tool for comprehensive financial data analysis including:
    - Real-time stock quotes and company information
    - Historical price data (intraday, daily, weekly, monthly)
    - Technical analysis with moving averages and volume indicators
    - Professional stock chart creation (candlestick, line, area)
    - Multi-stock comparison charts with multiple layouts
    - Market trend analysis and volatility assessment
    - Marketstack API integration for market data
    - Any financial data query requiring data retrieval or visualization
    
    Input: Natural language query about financial data or analysis.""",
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
    description="""Use this tool for creating charts and visualizations by executing Python code in a sandboxed environment:
    
    **Capabilities:**
    - Execute Python code to generate charts (matplotlib, seaborn, plotly, etc.)
    - Generate professional static chart images as PNG files
    - Handle various data formats and visualization requirements
    - Automatically save and display charts
    
    **Supported Libraries:**
    - matplotlib (line, bar, scatter, pie, histogram, box plots, etc.)
    - seaborn (advanced statistical visualizations)
    - plotly (interactive charts)
    - pandas (data manipulation and plotting)
    - numpy (numerical operations)
    
    **How it Works:**
    1. The agent generates complete, executable Python code
    2. Code is executed in a secure, isolated sandbox environment
    3. Generated PNG charts are automatically saved and embedded
    4. Charts are displayed above the response to the user
    
    **Code Requirements:**
    - Must import necessary libraries (matplotlib, numpy, pandas, etc.)
    - Must use plt.savefig() or similar to generate PNG output
    - Code executes with a 30-second timeout
    
    **Important:**
    - Charts are automatically displayed above the response after creation
    - Do NOT add chart HTML, image data, or chart content to the answer
    - Focus on explaining the visualization and insights
    
    Input: Natural language request with data to visualize (the agent will generate the Python code).""",
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
