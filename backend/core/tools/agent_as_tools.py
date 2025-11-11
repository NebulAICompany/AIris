from agents import Agent
from backend.core.prompts import finance_agent_prompt, office_agent_prompt, news_summarization_prompt, plotting_prompt
from backend.core.tools.mcp import finance_mcp_server
from .office import *
from backend.shared.constants import OPENAI_MODEL
from backend.utils.plotting import get_suitable_plot_types, create_html_plot

office_tools = [
    create_excel_file,
    create_word_document,
    create_powerpoint_presentation,
    add_powerpoint_slide,
    modify_word_content,
    modify_excel_cells,
    create_excel_charts,
]

finance_agent = Agent(
    name="Finance Agent",
    instructions=finance_agent_prompt,
    model=OPENAI_MODEL,
    mcp_servers=[finance_mcp_server],
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

plotting_agent = Agent(
    name="Plotting Agent",
    instructions=plotting_prompt,
    model=OPENAI_MODEL,
    tools=[get_suitable_plot_types, create_html_plot],
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

plotting_agent_tool = plotting_agent.as_tool(
    tool_name="plotting_agent",
    tool_description="""Use this tool for creating necessary configurations for interactive HTML plots from data:
    - Output should be a JSON object with the following fields:
        - title: str - The title of the plot
        - x_label: str - The label of the x-axis
        - y_label: str - The label of the y-axis
        - column_names: list[str] - The names of the columns
        - x_values: list[str] - The values of the x-axis
        - colors: list[str] - The colors of the plot
        - width: int - The width of the plot
        - height: int - The height of the plot
        - stacked: bool - Whether the plot is stacked
        - orientation: str - The orientation of the plot
    - Create necessary configurations for the plot
    - Do not add chart HTML or chart content to the answer""",
)