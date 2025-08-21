from agents import Agent
from backend.core.prompts import finance_agent_prompt, office_agent_prompt
from backend.core.tools.mcp import finance_mcp_server
from .office import *

office_tools = [create_excel_file, create_word_document,
                  create_powerpoint_presentation, add_powerpoint_slide, modify_word_content,
                  modify_excel_cells, create_excel_charts]

finance_agent = Agent(
    name="Finance Agent",
    instructions=finance_agent_prompt,
    mcp_servers=[finance_mcp_server],
)

office_agent = Agent(
    name="office_agent",
    instructions=office_agent_prompt,
    tools=[
        *office_tools,
    ],
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
    - Alpha Vantage API integration for market data
    - Any financial data query requiring data retrieval or visualization""",
)
