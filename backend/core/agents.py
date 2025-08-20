from agents import Agent
from .prompts import wolfram_instructions, rag_agent_instructions
from typing import List
from .tools.api import web_search_tool, wolfram_alpha_query
from .tools.agent_as_tools import finance_agent_tool, office_agent_tool
from .tools.visual import image_visualizer, redescribe_image_content

rag_agent_as_tools = [
    finance_agent_tool,
    office_agent_tool,
    wolfram_alpha_query,
    image_visualizer,
    redescribe_image_content,
]


def create_rag_agent(
    local_context: str,
    web_search_enabled: bool,
    query: str,
    instruction: str = None,
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
        for msg in conversation_history[-5:]:  # Show last 5 messages
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_context_part += f"{role}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}\n"
        conversation_context_part += "\n"

    # Start with a fresh list to avoid mutating the module-level list
    tools = [*rag_agent_as_tools]
    if web_search_enabled:
        tools.append(web_search_tool)

    agent_instructions = rag_agent_instructions.format(
        wolfram_instructions=wolfram_instructions,
        local_context=local_context,
        web_context_part=web_context_part,
        conversation_context_part=conversation_context_part,
        query=query,
        instruction_part=instruction_part,
    )

    agent = Agent(
        name="RAG_Assistant",
        instructions=agent_instructions,
        model="gpt-4o",
        tools=tools,
    )

    return agent
