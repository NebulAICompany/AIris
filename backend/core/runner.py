import time
from typing import Tuple, List
from backend.monitoring.metrics import llm_duration_seconds
from agents import Agent, Runner
from backend.core.agents import MainAgentResponse


async def generate_answer(prompt: str, agent: Agent) -> Tuple[str, List[str]]:
    """
    Generate answer from agent and extract used tools

    Returns:
        Tuple[str, List[str]]: (answer, list of used tool names)
    """
    try:
        start_time = time.time()

        # Run the agent
        result = await Runner.run(agent, prompt)

        # Extract structured output
        answer = ""
        used_tools = []

        if hasattr(result, "final_output"):
            final_output = result.final_output

            if isinstance(final_output, MainAgentResponse):
                answer = final_output.answer.strip()
                used_tools = final_output.used_tools or []
            else:
                # Fallback: treat as string
                answer = str(final_output).strip()

        duration = time.time() - start_time
        llm_duration_seconds.observe(duration)

        return answer, used_tools
    except Exception as e:
        error_msg = f"LLM yanıtı alınamadı: {str(e)}"
        return error_msg, []
