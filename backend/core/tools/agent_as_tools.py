import json
from typing import Any, Dict
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain.agents import create_agent
from langgraph.config import get_stream_writer
from backend.shared.logger import get_logger
from backend.core.prompts import (
    finance_agent_prompt,
    office_agent_prompt,
    plotting_prompt,
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

office_tools = [
    create_excel_file,
    create_word_document,
    modify_word_content,
    modify_excel_cells,
    create_excel_charts,
    create_powerpoint_from_code,
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
    middleware=[
        ToolCallLimitMiddleware(
            tool_name="create_powerpoint_from_code",
            run_limit=1,
            exit_behavior="continue",
        ),
    ],
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

tcmb_data_agent = create_agent(
    model=ANTHROPIC_MODEL,
    tools=tcmb_tools,
    system_prompt=tcmb_data_agent_prompt.format(
        current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ),
)


logger = get_logger("SUBAGENT_STREAMING")


class InnerToolCallbackHandler(BaseCallbackHandler):
    """
    Callback handler that captures inner tool calls and queues them
    for later emission to the parent stream.
    """
    
    def __init__(self, agent_name: str, event_queue: list):
        self.agent_name = agent_name
        self.event_queue = event_queue  # Shared list to queue events
        self.current_tool = None
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts - emit inner_tool_start event."""
        tool_name = serialized.get("name", "unknown")
        self.current_tool = tool_name
        
        # Priority list of parameters to look for (most descriptive first)
        param_priority = ["query", "content", "file_name", "symbol", "code", "prompt"]
        
        # Try to extract a descriptive parameter from various sources
        query = None
        try:
            input_data = None
            
            # First check kwargs for inputs
            inputs = kwargs.get("inputs", {})
            if isinstance(inputs, dict):
                input_data = inputs
            # Then try parsing input_str
            elif isinstance(input_str, str) and input_str:
                if input_str.startswith("{"):
                    input_data = json.loads(input_str)
                elif not input_str.startswith("<") and len(input_str) < 300:
                    # For simple string inputs (not XML/HTML), use directly
                    query = input_str
            elif isinstance(input_str, dict):
                input_data = input_str
            
            # Extract from input_data based on priority
            if input_data and isinstance(input_data, dict) and not query:
                for param in param_priority:
                    if param in input_data and input_data[param]:
                        val = input_data[param]
                        if isinstance(val, str) and len(val) > 0:
                            query = val
                            break
                        
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Could not extract query: {e}")
        
        logger.info(f"[{self.agent_name}] Callback: Inner tool started: {tool_name}, query: {query[:50] if query else 'None'}...")
        event_data = {
            "event": "inner_tool_start",
            "agent": self.agent_name,
            "tool_name": tool_name,
        }
        if query:
            event_data["query"] = query[:200] if len(str(query)) > 200 else str(query)
        # Queue the event for later emission
        self.event_queue.append(event_data)
    
    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool ends - queue inner_tool_end event."""
        tool_name = self.current_tool or "unknown"
        logger.info(f"[{self.agent_name}] Callback: Inner tool ended: {tool_name}")
        self.event_queue.append({
            "event": "inner_tool_end",
            "agent": self.agent_name,
            "tool_name": tool_name,
        })
        self.current_tool = None
    
    def on_tool_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        """Called when a tool errors - queue inner_tool_end event with error."""
        tool_name = self.current_tool or "unknown"
        logger.warning(f"[{self.agent_name}] Callback: Inner tool error: {tool_name} - {error}")
        self.event_queue.append({
            "event": "inner_tool_end",
            "agent": self.agent_name,
            "tool_name": tool_name,
        })
        self.current_tool = None


# Helper function to stream sub-agent and emit inner tool events
async def stream_subagent_with_events(agent, agent_name: str, query: str):
    """
    Stream a sub-agent's execution and emit custom events for inner tool calls.
    Uses callbacks to capture events and emits them via writer during stream iteration.
    Returns the final content from the agent.
    """
    try:
        writer = get_stream_writer()
        logger.debug(f"Got stream writer for {agent_name}")
    except Exception as e:
        # If we're not in a streaming context, writer won't work
        # Fall back to simple ainvoke
        logger.warning(f"Could not get stream writer for {agent_name}: {e}")
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": query}]}
        )
        return result["messages"][-1].content
    
    final_content = None
    
    # Shared event queue - callbacks will append events here
    event_queue = []
    
    # Create callback handler that queues events
    callback_handler = InnerToolCallbackHandler(agent_name, event_queue)
    
    # Emit subagent start event
    logger.debug(f"Emitting subagent_start for {agent_name}")
    writer({"event": "subagent_start", "agent": agent_name, "query": query[:100]})
    
    # Stream the sub-agent's updates with callback for tool events
    async for sub_chunk in agent.astream(
        {"messages": [{"role": "user", "content": query}]},
        config={"callbacks": [callback_handler]},
        stream_mode="updates",
    ):
        # Emit any queued events from callbacks
        while event_queue:
            event = event_queue.pop(0)
            logger.debug(f"Emitting queued event: {event['event']} - {event.get('tool_name', 'N/A')}")
            writer(event)
        
        # Process chunks to capture final content
        if isinstance(sub_chunk, dict):
            for node_name, node_data in sub_chunk.items():
                # Capture final content from agent/model node
                if node_name in ("agent", "model") and isinstance(node_data, dict):
                    messages = node_data.get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "content") and msg.content:
                            content = msg.content
                            # Handle Anthropic's list content format
                            if isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        final_content = block.get("text", "")
                            elif isinstance(content, str):
                                final_content = content
    
    # Emit any remaining queued events
    while event_queue:
        event = event_queue.pop(0)
        logger.debug(f"Emitting final queued event: {event['event']} - {event.get('tool_name', 'N/A')}")
        writer(event)
    
    # Emit subagent end event
    logger.debug(f"Emitting subagent_end for {agent_name}")
    writer({"event": "subagent_end", "agent": agent_name})
    
    return final_content


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
    content = await stream_subagent_with_events(finance_agent, "finance_agent", query)
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
    content = await stream_subagent_with_events(office_agent, "microsoft_office_operations", query)
    return content


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
    content = await stream_subagent_with_events(plotting_agent, "plotting_agent", query)
    return content


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
    content = await stream_subagent_with_events(tcmb_data_agent, "tcmb_economic_data", query)
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
    call_tcmb_agent,
]
