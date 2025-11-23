import time
from typing import Tuple, List, Dict
from backend.monitoring.metrics import llm_duration_seconds
from agents import Agent, Runner
from backend.core.agents import MainAgentResponse


async def generate_answer(
    prompt: str, agent: Agent
) -> Tuple[str, List[str], List[Dict[str, str]]]:
    """
    Generate answer from agent and extract used tools and web sources

    Returns:
        Tuple[str, List[str], List[Dict[str, str]]]: (answer, list of used tool names, list of web sources with name and url)
    """
    try:
        start_time = time.time()

        # Run the agent
        result = await Runner.run(agent, prompt)

        # Extract structured output
        answer = ""
        used_tools = []
        web_sources = []

        if hasattr(result, "final_output"):
            final_output = result.final_output

            if isinstance(final_output, MainAgentResponse):
                answer = final_output.answer.strip()
                used_tools = final_output.used_tools or []
                # Convert WebSource objects to dicts
                web_sources = [
                    {"name": ws.name, "url": ws.url}
                    for ws in (final_output.web_sources or [])
                ]
            else:
                # Fallback: treat as string
                answer = str(final_output).strip()

        duration = time.time() - start_time
        llm_duration_seconds.observe(duration)

        return answer, used_tools, web_sources
    except Exception as e:
        error_msg = f"LLM yanıtı alınamadı: {str(e)}"
        return error_msg, [], []
