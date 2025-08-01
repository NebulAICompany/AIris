from agents import Agent
from .tools.mcp import alpha_vantage_mcp_server
from .prompts import wolfram_instructions
from typing import List
from .tools.api import wolfram_alpha_query, web_search_tool
from .tools.base_tools import rag_agent_as_tools


def create_rag_agent(
    local_context: str,
    web_search_enabled: bool,
    query: str,
    instruction: str = None,
    wolfram_enabled: bool = False,
    conversation_history: List = None,
) -> Agent:

    instruction_part = f"\n\nSpecial Instruction: {instruction}" if instruction else ""

    # Include web context
    web_context_part = (
        f"Use your web_search_tool to research the topic on the internet and "
        if web_search_enabled
        else ""
    )

    # Format conversation history
    conversation_context_part = ""
    if conversation_history and len(conversation_history) > 0:
        conversation_context_part = "\n**Conversation History:**\n"
        for i, msg in enumerate(conversation_history[-5:]):  # Show last 5 messages
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_context_part += f"{role}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}\n"
        conversation_context_part += "\n"

    tools = rag_agent_as_tools
    if web_search_enabled:
        tools.append(web_search_tool)

    if wolfram_enabled:
        tools.append(wolfram_alpha_query)

    agent_instructions = f"""You are an advanced RAG (Retrieval-Augmented Generation) Assistant. 

**Wolfram Instructions:**
{wolfram_instructions}

**Local Context Information:**
{local_context}

**Web Search Status:** {web_context_part}
{conversation_context_part}
**Current Query:**
{query}{instruction_part}

**Task Definition and Responsibilities:**

**Main Tasks:**
1. **Information Analysis:** Analyze the query and determine which sources you need to use
2. **Smart Routing:** Use specialized agents correctly
3. **Comprehensive Response:** Provide detailed and accurate responses with available information
4. **Source Documentation:** Provide metadata for the information you use

**Processing Protocols:**

**For Office Operations:**
Use the office_operations tool in any of the following cases:
- Creating and editing Word documents
- Creating Excel files and data processing
- Extracting Excel files from table data
- Document format conversion
- Any operation requiring Microsoft Office applications

**For Financial Data Analysis:**
Use the financial_data_analysis tool in any of the following cases:
- Stock prices and quotations
- Company financial information (sector, market value)
- Cryptocurrency rates and analysis
- Historical price data and time series
- Options chain data
- Technical analysis and market trends
- Any financial data query or analysis

**Quality Standards:**
- Provide accurate and current information
- Document your sources transparently
- Express uncertainties clearly
- Use user-friendly and understandable language
- Provide structured and organized responses

**Response Format:**
At the end of each response, show the metadata of the sources you used in the following format:

```
Used Information Metadata:
- Source: (Actual source file name)
- Date: (Document date if available)
- Category: (Content category)
```

NOTE: If any information is not available, you can skip that line. Do not use placeholders or empty values ([...], None, etc.).

**Critical Rules:**
- Do not speculate on topics you don't know
- Use specialized agents for the correct function
- Always prefer reliable sources
- Protect user privacy and data security

Now analyze the query and prepare the most appropriate response! """

    agent = Agent(
        name="RAG_Assistant",
        instructions=agent_instructions,
        model="gpt-4.1",
        tools=tools,
    )

    return agent


async def main():
    await alpha_vantage_mcp_server.connect()
    #   result = await Runner.run(alpha_vantage_agent, "What is Tesla stock price?")
    #   print(result)


# TODO: This main function is only for connection reminder
