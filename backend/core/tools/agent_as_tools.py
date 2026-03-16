import json
from typing import Any, Dict, Optional
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain.agents import create_agent
from langgraph.config import get_stream_writer
from backend.shared.logger import get_logger
from backend.core.prompts import (
    finance_agent_prompt,
    file_agent_prompt,
    plotting_prompt,
    tcmb_data_agent_prompt,
)
from langchain.agents.middleware import ToolCallLimitMiddleware
from datetime import datetime
from backend.core.runner import extract_query_from_args, extract_text_tokens
from .file_tools import (
    create_excel_file,
    create_word_document,
    create_powerpoint_from_code,
    modify_word_content,
    modify_excel_cells,
    create_excel_charts,
    read_excel_file,
    read_word_document,
    read_powerpoint_file,
    describe_file_image,
    execute_file_code,
    list_created_files,
    get_available_charts,
    get_generated_files,
    clear_generated_files,
    set_generated_files,
)
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
from backend.shared.constants import CURRENT_MODEL
from backend.core.tools.plotting import (
    create_custom_chart_from_code,
    create_financial_stock_chart,
)

file_tools = [
    create_excel_file,
    create_word_document,
    create_powerpoint_from_code,
    modify_word_content,
    modify_excel_cells,
    create_excel_charts,
    read_excel_file,
    read_word_document,
    read_powerpoint_file,
    describe_file_image,
    execute_file_code,
    list_created_files,
    get_available_charts,
]

tcmb_tools = [
    get_tcmb_subcategories,
    get_tcmb_series,
    get_tcmb_data,
]

finance_tools = [
    get_eod_data,
    #get_intraday_data,
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
    model=CURRENT_MODEL,
    tools=finance_tools,
    system_prompt=finance_agent_prompt,
)

file_agent = create_agent(
    model=CURRENT_MODEL,
    tools=file_tools,
    system_prompt=file_agent_prompt,
    middleware=[
        ToolCallLimitMiddleware(
            tool_name="create_powerpoint_from_code",
            run_limit=2,
            exit_behavior="continue",
        ),
        ToolCallLimitMiddleware(
            tool_name="execute_file_code",
            run_limit=2,
            exit_behavior="continue",
        ),
    ],
)


plotting_agent = create_agent(
    model=CURRENT_MODEL,
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
    model=CURRENT_MODEL,
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
        self.event_queue = event_queue
        self.current_tool = None
    
    def _parse_input_data(self, input_str: str, kwargs: Dict) -> tuple[Optional[Dict], Optional[str]]:
        """Parse input data from various sources. Returns (input_data, simple_query)."""
        inputs = kwargs.get("inputs", {})
        if isinstance(inputs, dict) and inputs:
            return inputs, None
        
        if isinstance(input_str, dict):
            return input_str, None
        
        if isinstance(input_str, str) and input_str:
            if input_str.startswith("{"):
                try:
                    return json.loads(input_str), None
                except json.JSONDecodeError:
                    pass
            elif not input_str.startswith("<") and len(input_str) < 300:
                return None, input_str
        
        return None, None
    
    def _extract_tool_specific_query(self, tool_name: str, input_data: Dict) -> Optional[str]:
        """Extract query with special formatting for specific tools."""
        if tool_name == "get_tcmb_data":
            serie_codes = input_data.get("serie_codes")
            if serie_codes:
                codes_str = str(serie_codes) if isinstance(serie_codes, list) else serie_codes
                start_date = input_data.get("start_date")
                end_date = input_data.get("end_date")
                date_range = f", {start_date} to {end_date}" if start_date and end_date else ""
                return f"{codes_str}{date_range}"
        
        elif tool_name == "get_tcmb_subcategories":
            category_id = input_data.get("category_id")
            if category_id is not None:
                return f"category_id: {category_id}"
        
        elif tool_name == "get_tcmb_series":
            datagroup_code = input_data.get("datagroup_code")
            if datagroup_code:
                return f"datagroup: {datagroup_code}"
        
        elif tool_name == "create_financial_stock_chart":
            symbols = input_data.get("symbols")
            if symbols:
                symbols_str = ", ".join(symbols) if isinstance(symbols, list) else symbols
                chart_type = input_data.get("chart_type", "candlestick")
                period = input_data.get("period", "daily")
                return f"{symbols_str} ({chart_type}, {period})"
        
        elif tool_name in ("get_eod_data", "get_intraday_data", "get_splits_data", "get_dividends_data"):
            symbols = input_data.get("symbols")
            if symbols:
                return f"symbols: {symbols}"
        
        return None
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts."""
        tool_name = serialized.get("name", "unknown")
        self.current_tool = tool_name
        
        query = None
        try:
            input_data, simple_query = self._parse_input_data(input_str, kwargs)
            
            if simple_query:
                query = simple_query
            elif input_data and isinstance(input_data, dict):
                # Try tool-specific extraction first
                query = self._extract_tool_specific_query(tool_name, input_data)
                # Fall back to generic extraction
                if not query:
                    query = extract_query_from_args(input_data)
        except Exception:
            pass
        
        event_data = {
            "event": "inner_tool_start",
            "agent": self.agent_name,
            "tool_name": tool_name,
        }
        if query:
            event_data["query"] = query[:200] if len(str(query)) > 200 else str(query)
        self.event_queue.append(event_data)
    
    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool ends."""
        tool_name = self.current_tool or "unknown"
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
    except Exception as e:
        # Not in streaming context - fall back to simple invoke
        logger.warning(f"Could not get stream writer for {agent_name}: {e}")
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": query}]}
        )
        return result["messages"][-1].content
    
    final_content = None
    
    # Shared event queue - callbacks will append events here
    event_queue = []
    
    callback_handler = InnerToolCallbackHandler(agent_name, event_queue)
    
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
            writer(event)
        
        # Process chunks to capture final content
        if isinstance(sub_chunk, dict):
            for node_name, node_data in sub_chunk.items():
                if node_name in ("agent", "model") and isinstance(node_data, dict):
                    for msg in node_data.get("messages", []):
                        if hasattr(msg, "content") and msg.content:
                            # Use shared function for content extraction
                            for text in extract_text_tokens(msg.content):
                                final_content = text
    
    # Emit any remaining queued events
    while event_queue:
        writer(event_queue.pop(0))
    
    writer({"event": "subagent_end", "agent": agent_name})
    
    return final_content


# Wrap subagents as tools for the main agent
@tool(
    "finance_agent",
    description=(
        "Use this tool ONLY when specific financial market data is required. "
        "This tool retrieves and analyzes structured financial market data, including "
        "end-of-day prices (OHLCV), dividends, splits, indexes, ticker and exchange metadata, "
        "currencies, timezones, and historical time-series. "
        "It supports multi-symbol and multi-timeframe analysis over this data. "
        "Input must be a natural language request describing the desired financial data "
        "(e.g., 'get daily OHLCV for AAPL for the last 30 days')."
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
    "file_operations",
    description=(
        "Use this tool for file and document operations: creating, reading, modifying, "
        "and analyzing Excel workbooks, Word documents, PowerPoint presentations, and images. "
        "It can generate new files, read existing file contents, modify documents, "
        "understand images via vision AI, and run Python code in a sandbox for complex file tasks. "
        "Input must be a natural language request describing the desired file operation "
        "(for example, 'create an Excel file with this table' or 'read the contents of report.docx')."
    ),
)
async def call_file_agent(query: str) -> str:
    """Route file and document requests to the file operations agent.

    Args:
        query: Natural language request describing a file operation.
    """
    content = await stream_subagent_with_events(file_agent, "file_operations", query)
    return content


@tool(
    "plotting_agent",
    description=(
        "Use this tool when a visual chart or plot is explicitly required to answer the user’s request. "
        "This tool creates data visualizations, including financial market charts "
        "(candlestick, OHLC, line, area with technical indicators, volume) and custom non-financial charts "
        "(statistical, scientific, or exploratory) from Python code."
        "Input must be a natural language request describing the chart needed "
        "and whether the data is financial market data or custom/tabular data."),
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
        "Use this tool ONLY to retrieve structured Turkish Central Bank (TCMB) "
        "economic data from the EVDS system."
        "It provides time-series for economic indicators such as "
        "exchange rates, interest rates, inflation, balance of payments, reserves, "
        "money and credit statistics, price indices, and survey data. "
        "Input must be a natural language query specifying the indicator(s) and "
        "time period of interest "
        "(e.g., 'monthly CPI inflation and policy rate for the last five years'). "
        "Best used for queries requiring official Turkish macroeconomic or monetary data."
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
    call_file_agent,
    call_plotting_agent,
    call_tcmb_agent,
]
