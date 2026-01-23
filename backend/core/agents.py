from langchain.agents import create_agent
from .prompts import (
    main_agent_instructions,
    news_chat_agent_instructions,
)
from typing import List
from pydantic import BaseModel, Field
from langchain.agents.structured_output import ToolStrategy
from datetime import datetime
from .tools.api import (
    web_search_tool,
    wolfram_alpha_query,
    get_uploaded_files_count,
    list_uploaded_files,
)
from .tools.agent_as_tools import main_agent_subagents
from .tools.rag import search_local_documents
from backend.shared.constants import OPENAI_MODEL, ANTHROPIC_MODEL


class NewsCluster(BaseModel):
    """Represents a cluster of related news articles"""

    cluster_id: int = Field(..., description="Unique identifier for the cluster")
    story_theme: str = Field(
        ..., description="Brief description of the underlying story or theme"
    )
    article_indices: List[int] = Field(
        ..., description="List of article indices that belong to this cluster"
    )
    reasoning: str = Field(
        ..., description="Explanation of why these articles belong together"
    )


class NewsClusteringResponse(BaseModel):
    """Structured output for news clustering agent"""

    clusters: List[NewsCluster] = Field(
        default_factory=list,
        description="List of clusters containing related articles covering the same story",
    )
    single_articles: List[int] = Field(
        default_factory=list,
        description="List of article indices that don't belong to any cluster (standalone articles)",
    )
    analysis: str = Field(
        ...,
        description="Overall analysis of the news landscape and clustering decisions",
    )


class NewsSummarizationResponse(BaseModel):
    """Structured output for news summarization agent"""

    unified_title: str = Field(
        ..., description="Comprehensive unified title that captures the complete story"
    )
    unified_description: str = Field(
        ...,
        description="Detailed, comprehensive description (500+ words) including all information from all sources. Use {{IMAGE_LEAD}}, {{IMAGE_MID_1}}, {{IMAGE_MID_2}} markers where appropriate.",
    )


main_agent_tools = [
    search_local_documents,
    wolfram_alpha_query,
    get_uploaded_files_count,
    list_uploaded_files,
]


def create_main_agent(
    web_search_enabled: bool = False,
    instruction: str = None,
    conversation_history: List = None,
):
    """
    Create a Deep Agent for main assistant functionality with agentic RAG.

    Returns a Deep Agent configured with tools, subagents, and custom instructions.
    The agent can use search_local_documents tool to retrieve information on demand.
    """
    instruction_part = (
        f"**Special Instructions:**\n{instruction}\n" if instruction else ""
    )

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
    tools = [*main_agent_tools, *main_agent_subagents]
    if web_search_enabled:
        tools.append(web_search_tool)

    agent_instructions = main_agent_instructions.format(
        current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        web_context_part=web_context_part,
        conversation_context_part=conversation_context_part,
        instruction_part=instruction_part,
    )

    agent = create_agent(
        model=ANTHROPIC_MODEL,
        tools=tools,
        system_prompt=agent_instructions,
    )

    return agent


def create_news_summarization_agent(
    instructions: str,
    web_search_enabled: bool,
):
    """
    Create a specialized Deep Agent for news summarization with news context and web search capabilities.
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

    agent = create_agent(
        model="gpt-4o-mini",
        tools=[web_search_tool] if web_search_enabled else [],
        system_prompt=agent_instructions,
        response_format=ToolStrategy(NewsSummarizationResponse),
    )
    return agent


def create_clustering_agent(instructions: str):
    """Create specialized clustering Deep Agent"""
    agent = create_agent(
        model="gpt-4o-mini",
        tools=[],
        system_prompt=instructions,
        response_format=ToolStrategy(NewsClusteringResponse),
    )
    return agent


def create_news_chat_agent(
    news_context: str,
    conversation_history: List = None,
):
    """
    Create a specialized Deep Agent for news chat queries with news context and web search capabilities.
    """
    # Format conversation history
    conversation_context_part = ""
    if conversation_history and len(conversation_history) > 0:
        conversation_context_part = "\n**Conversation History:**\n"
        for msg in conversation_history[-5:]:  # Show last 5 messages
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_context_part += f"{role}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}\n"
        conversation_context_part += "\n"

    tools = [time_now]
    tools.append(web_search_tool)

    agent_instructions = news_chat_agent_instructions.format(
        current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        news_context=news_context,
        conversation_context_part=conversation_context_part,
    )

    agent = create_agent(
        model="gpt-4o-mini",
        tools=tools,
        system_prompt=agent_instructions,
    )

    return agent


def create_translation_agent(instructions: str):
    """Create a specialized translation Deep Agent"""
    agent = create_agent(
        model="gpt-4o-mini",
        tools=[],
        system_prompt=instructions,
    )
    return agent
