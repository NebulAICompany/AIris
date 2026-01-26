from langchain_core.tools import tool
from langchain.agents import create_agent
from backend.core.prompts import (
    finance_agent_prompt,
    office_agent_prompt,
    plotting_prompt,
    powerpoint_agent_prompt,
    tcmb_data_agent_prompt,
)
from langchain.agents.middleware import ToolCallLimitMiddleware
from datetime import datetime
from .office import *
from .tcmb_data import get_tcmb_subcategories, get_tcmb_series, get_tcmb_data
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
from backend.shared.constants import OPENAI_MODEL, ANTHROPIC_MODEL
from backend.core.tools.plotting import (
    create_custom_chart_from_code,
    create_financial_stock_chart,
)
from backend.core.tools.powerpoint import (
    create_powerpoint_from_code,
)

office_tools = [
    create_excel_file,
    create_word_document,
    modify_word_content,
    modify_excel_cells,
    create_excel_charts,
]

tcmb_tools = [
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
    model=ANTHROPIC_MODEL,
    tools=finance_tools,
    system_prompt=finance_agent_prompt,
)

office_agent = create_agent(
    model=ANTHROPIC_MODEL,
    tools=office_tools,
    system_prompt=office_agent_prompt,
)


plotting_agent = create_agent(
    model=ANTHROPIC_MODEL,
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

powerpoint_agent = create_agent(
    model=ANTHROPIC_MODEL,
    tools=[
        create_powerpoint_from_code,
    ],
    system_prompt=powerpoint_agent_prompt,
    middleware=[
        ToolCallLimitMiddleware(
            tool_name="create_powerpoint_from_code",
            run_limit=1,
            exit_behavior="continue",
        ),
    ],
)

tcmb_data_agent = create_agent(
    model=ANTHROPIC_MODEL,
    tools=tcmb_tools,
    system_prompt=tcmb_data_agent_prompt.format(
        current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ),
)


# Wrap subagents as tools for the main agent
@tool(
    "finance_agent",
    description=(
        "Use this tool for retrieving and analyzing financial market data. "
        "It can fetch intraday and end-of-day prices (OHLCV), dividends, splits, "
        "indexes, ticker and exchange info, currencies, and timezones, and perform "
        "multi-symbol and multi-timeframe analysis over this data. "
        "Input must be a natural language request describing the desired financial data "
        "or analysis (for example, 'get daily OHLCV for AAPL for the last 30 days')."
    ),
    response_format="content_and_artifact",
)
async def call_finance_agent(query: str) -> str:
    """Route a financial data or analysis request to the finance specialist agent.

    Args:
        query: Natural language request about financial data retrieval or analysis.
    """
    result = await finance_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    content = result["messages"][-1].content
    artifact = {
        "name": "Marketstack API",
        "description": f"Financial data: {query[:50]}...",
    }
    return content, artifact

@tool(
    "microsoft_office_operations",
    description=(
        "Use this tool for Microsoft Office document operations, including creating "
        "and updating Excel workbooks, Word documents, and PowerPoint presentations. "
        "It can generate new files, modify existing ones, and perform basic document "
        "processing or format conversions using Word, Excel, or PowerPoint. "
        "Input must be a natural language request describing the desired Office action "
        "(for example, 'create an Excel file with this table and add a chart')."
    ),
)
async def call_office_agent(query: str) -> str:
    """Route Office document requests to the Office operations agent.

    Args:
        query: Natural language request describing a Word, Excel, or PowerPoint operation.
    """
    result = await office_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


@tool(
    "plotting_agent",
    description=(
        "Use this tool for all chart creation and data visualization. "
        "It can create financial stock charts (candlestick, OHLC, line, area, "
        "with technical indicators and volume) using market data, and it can "
        "generate custom, non-financial visualizations (statistical, scientific, "
        "or exploratory charts) from Python code. "
        "Input must be a natural language request describing the chart needed "
        "and whether the data is financial market data or custom/tabular data."
    ),
)
async def call_plotting_agent(query: str) -> str:
    """Route chart and visualization requests to the plotting agent.

    Args:
        query: Natural language description of the chart or visualization to create.
    """
    result = await plotting_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


@tool(
    "powerpoint_agent",
    description=(
        "Use this tool for creating PowerPoint presentations with custom designs and layouts. "
        "It can generate professional presentations with multiple slides, custom formatting, "
        "shapes, images, tables, and charts using python-pptx library. "
        "Input must be a natural language request describing the presentation to create "
        "(for example, 'create a 10-slide presentation about artificial intelligence with images and charts')."
    ),
)
async def call_powerpoint_agent(query: str) -> str:
    """Route PowerPoint presentation creation requests to the PowerPoint agent.

    Args:
        query: Natural language description of the PowerPoint presentation to create.
    """
    result = await powerpoint_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["messages"][-1].content


@tool(
    "tcmb_economic_data",
    description=(
        "Use this tool to retrieve and analyze Turkish Central Bank (TCMB) economic data "
        "from the EVDS system. It can fetch time series for economic indicators such as "
        "exchange rates, interest rates, inflation, balance of payments, reserves, "
        "money and credit statistics, price indices, and survey data. "
        "Input must be a natural language query about Turkish macroeconomic or monetary "
        "policy data, specifying the indicators and time period of interest "
        "(for example, 'monthly CPI inflation and policy rate for the last five years')."
        "Best for queries about Turkish economic indicators, monetary policy data, financial statistics, and macroeconomic trends."
    ),
   response_format="content_and_artifact",
)
async def call_tcmb_agent(query: str):
    """Route Turkish economic data requests to the TCMB specialist agent.
      
    Args:
        query: Natural language request describing the TCMB/EVDS data to retrieve or analyze.
    """
    result = await tcmb_data_agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    content = result["messages"][-1].content
    artifact = {
        "name": "TCMB EVDS",
        "description": f"Turkish economic data: {query[:50]}...",
    }
    return content, artifact

# List of subagent tools for the main agent
main_agent_subagents = [
    call_finance_agent,
    call_office_agent,
    call_plotting_agent,
    call_powerpoint_agent,
    call_tcmb_agent,
]
