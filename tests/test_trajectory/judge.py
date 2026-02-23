# evals/trajectory_judge.py
from agentevals.trajectory.llm import (
    create_trajectory_llm_as_judge,
)
from langchain_core.prompts import ChatPromptTemplate

TRAJECTORY_PIPELINE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert evaluator of AI agent execution trajectories."),
    ("user", """You are evaluating the QUALITY and EFFICIENCY of an AI agent's execution TRAJECTORY.

You are given the full message history, including:
- the user's query,
- the agent's internal reasoning steps (if present),
- tool calls and their inputs/outputs,
- final answer.

Your goals:
1. Detect UNNECESSARY actions:
   - tool or sub-agent calls that did not contribute to the final answer,
   - redundant or repeated calls with the same or very similar inputs,
   - obvious overuse of tools where simple reasoning would suffice.

2. Detect UNSUCCESSFUL tool calls:
   - calls that errored, timed out, or returned malformed/empty results,
   - calls whose outputs were clearly not useful for the task.

3. Detect UNUSED outputs:
   - tool outputs that were never referenced or used in later steps
     or in the final answer.

4. Give an OVERALL judgment of the trajectory quality.


     
For each evaluation, respond in STRICT JSON with this schema:

{{{{
  "score": 0 or 1,
  "reasoning": "...",
  "tool_summary": [
    {{{{
      "tool_name": "tcmb_economic_data",
      "total_calls": 3,
      "unnecessary_calls": 2,
      "comment": "..."
    }}}}
  ]
}}}}

Where:
- "score" = 1 if the trajectory is reasonable and efficient (no serious issues),
  and 0 if there are clear problems (wasted calls, failures, etc.).

Now evaluate the following trajectory:

---------------- TRAJECTORY START ----------------
{outputs}
---------------- TRAJECTORY END ----------------
""")
])

def create_trajectory_pipeline_judge(model: str = "openai:o3-mini"):
    return create_trajectory_llm_as_judge(
        model=model,
        prompt=TRAJECTORY_PIPELINE_PROMPT,
    )
