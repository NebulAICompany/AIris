import os
import time
from openai import OpenAI
from aiiris_backend.monitoring.metrics import llm_duration_seconds
from agents import Agent, Runner
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
import dotenv

env_path = PROJECT_ROOT / ".env"
dotenv.load_dotenv(env_path)
os.environ["OPENAI_API_KEY"] = "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"


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
