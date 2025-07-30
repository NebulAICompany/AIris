from agents import Agent
from backend.core.prompts import alpha_vantage_prompt, office_agent_prompt
from backend.core.tools.mcp import alpha_vantage_mcp_server
from backend.core.tools.base_tools import document_tools

alpha_vantage_agent = Agent(
    name="Alpha Vantage Finance Agent",
    instructions=alpha_vantage_prompt,
    mcp_servers=[alpha_vantage_mcp_server],
)


office_agent = Agent(
    name="office_agent",
    instructions=office_agent_prompt,
    tools=[
        *document_tools,
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

alpha_vantage_tool = alpha_vantage_agent.as_tool(
    tool_name="financial_data_analysis",
    tool_description="""Use this tool for financial data analysis including:
    - Stock quotes and company information
    - Cryptocurrency rates and analysis
    - Historical price data and time series
    - Option chain data and technical analysis
    - Market trends and volatility analysis
    - Any financial data query or analysis""",
)
