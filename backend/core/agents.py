from agents import Agent
from .prompts import (
    wolfram_instructions,
    rag_agent_instructions,
    news_chat_agent_instructions,
)
from typing import List
from .tools.api import web_search_tool, wolfram_alpha_query, time_now
from .tools.agent_as_tools import finance_agent_tool, office_agent_tool
from .tools.visual import image_visualizer, redescribe_image_content
from backend.shared.constants import OPENAI_MODEL, ANTHROPIC_MODEL

rag_agent_as_tools = [
    finance_agent_tool,
    office_agent_tool,
    wolfram_alpha_query,
    time_now,
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
        model=OPENAI_MODEL,
        tools=tools,
    )

    return agent


def create_news_summarization_agent(
    instructions: str,
    web_search_enabled: bool,
) -> Agent:
    """
    Create a specialized agent for news summarization with news context and web search capabilities.
    """
    # Include web context
    web_context_part = (
        f"Use your web_search_tool to research the topic on the internet and "
        if web_search_enabled
        else ""
    )
    agent_instructions = f"""
    {instructions}
    
    **Web Search Status:** {web_context_part}
    """

    agent = Agent(
        name="News_Summarization_Assistant",
        instructions=agent_instructions,
        model="gpt-4o-mini",
        tools=[web_search_tool],
    )
    return agent


def create_clustering_agent(instructions: str) -> Agent:
    """Create specialized clustering agent"""
    agent = Agent(
        name="Turkish_Financial_News_Clusterer",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[],  # No tools needed, pure text analysis
    )
    return agent


def create_news_chat_agent(
    news_context: str,
    query: str,
    conversation_history: List = None,
) -> Agent:
    """
    Create a specialized agent for news chat queries with news context and web search capabilities.
    """
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
    tools.append(web_search_tool)

    agent_instructions = news_chat_agent_instructions.format(
        wolfram_instructions=wolfram_instructions,
        news_context=news_context,
        conversation_context_part=conversation_context_part,
        query=query,
    )

    agent = Agent(
        name="News_Chat_Assistant",
        instructions=agent_instructions,
        model="gpt-4o-mini",
        tools=tools,
    )

    return agent


def create_translation_agent(instructions: str) -> Agent:
    """Create a specialized translation agent"""
    agent = Agent(
        name="Translation_Assistant",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[],
    )
    return agent
