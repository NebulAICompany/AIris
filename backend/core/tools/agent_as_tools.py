from backend.core.agents import office_agent, alpha_vantage_agent

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
