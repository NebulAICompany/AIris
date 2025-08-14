import time
from backend.monitoring.metrics import llm_duration_seconds
from agents import Agent, Runner

async def generate_answer(prompt: str, agent: Agent) -> str:
    try:
        start_time = time.time()

        # Run the agent
        result = await Runner.run(agent, prompt)

        # Extract the answer from the agent's response
        answer = result.final_output.strip()

        duration = time.time() - start_time
        llm_duration_seconds.observe(duration)

        return answer
    except Exception as e:
        return f"LLM yanıtı alınamadı: {str(e)}"
