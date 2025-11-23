from deepagents import SubAgent
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
from backend.core.tools.plotting import (
    get_suitable_plot_types,
    create_html_plot,
    extract_data_from_text,
    convert_to_plottable_format,
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

# Define subagents for Deep Agents
finance_subagent = SubAgent(
    name="finance_agent",
    description="""Use this subagent for comprehensive financial data analysis including:
    - Real-time stock quotes and company information
    - Historical price data (intraday, daily, weekly, monthly)
    - Technical analysis with moving averages and volume indicators
    - Professional stock chart creation (candlestick, line, area)
    - Multi-stock comparison charts with multiple layouts
    - Market trend analysis and volatility assessment
    - Marketstack API integration for market data
    - Any financial data query requiring data retrieval or visualization""",
    system_prompt=finance_agent_prompt,
    tools=finance_tools,
    model=OPENAI_MODEL,
)

office_subagent = SubAgent(
    name="office_operations",
    description="""Use this subagent for Microsoft Office operations including:
        - Creating Excel workbooks from structured data
        - Generating Word documents with custom content
        - Document processing and format conversion
        - Any task requiring Word or Excel functionality""",
    system_prompt=office_agent_prompt,
    tools=office_tools,
    model=OPENAI_MODEL,
)

plotting_subagent = SubAgent(
    name="plotting_agent",
    description="""Use this subagent for creating interactive HTML plots from various data sources:
    
    **Capabilities:**
    - Extract structured data from text, tables, JSON, CSV-like formats, markdown tables
    - Convert data into plottable formats (lists, numpy arrays, pandas DataFrames)
    - Determine the most suitable plot types for given data
    - Create professional interactive HTML plots with Plotly
    - Save charts to disk for display
    
    **Supported Plot Types:**
    line, bar, scatter, pie, histogram, box, heatmap, area, violin, bubble, 
    waterfall, radar, funnel, candlestick, treemap, scatter_3d
    
    **Input Data Formats:**
    - Markdown tables (| Col1 | Col2 | ...)
    - CSV/TSV text (comma or tab separated)
    - JSON objects or arrays
    - Python lists, dictionaries
    - Key-value pairs (Key: Value format)
    - Natural language descriptions with numbers
    
    **Important:**
    - Charts are automatically displayed above the response after creation
    - Do NOT add chart HTML or chart content to the answer
    - Focus on explaining the visualization and insights
    - This tool handles the complete workflow: data extraction → formatting → plot creation → saving""",
    system_prompt=plotting_prompt,
    tools=[
        extract_data_from_text,
        convert_to_plottable_format,
        get_suitable_plot_types,
        create_html_plot,
    ],
    model=OPENAI_MODEL,
)

tcmb_data_subagent = SubAgent(
    name="tcmb_economic_data",
    description="""Use this subagent for comprehensive Turkish Central Bank (TCMB) economic data retrieval and analysis:
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
    system_prompt=tcmb_data_agent_prompt,
    tools=tcmb_tools,
    model=OPENAI_MODEL,
)

news_summarization_subagent = SubAgent(
    name="financial_news_summarization",
    description="""Use this subagent for creating unified summaries from multiple financial news articles covering the same story:
    - Combine titles and descriptions from multiple news sources
    - Create concise, unified titles for clustered news stories
    - Generate comprehensive summaries that synthesize information from all sources
    - Maintain objectivity and financial accuracy
    - Format output as JSON with unified_title and unified_description fields
    - Best used when you have 2+ articles about the same financial event/story""",
    system_prompt=news_summarization_prompt,
    tools=[],  # This agent uses only LLM capabilities, no external tools
    model="gpt-4o-mini",
)

main_agent_subagents = [
    finance_subagent,
    office_subagent,
    plotting_subagent,
    tcmb_data_subagent,
    news_summarization_subagent,
]
