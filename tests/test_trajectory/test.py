# tests/test_trajectory_llm_judge.py
import asyncio
import random
from typing import List, Dict, Any

from langchain_core.messages import HumanMessage
from langsmith import Client

from backend.core.agents import create_main_agent
from judge import create_trajectory_pipeline_judge
from queries import TEST_QUERIES  # from section 2 above

client = Client()

def build_dataset_inputs(queries: List[str]) -> List[Dict[str, Any]]:
    """Convert raw queries into LangSmith-compatible inputs."""
    return [{"messages": [HumanMessage(content=q)]} for q in queries]

async def run_agent_on_input(agent, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run your agent and return its outputs (messages with traces)."""
    # If you use LangChain agents, usually agent.invoke expects `{"messages": [...]}`.
    return await agent.ainvoke(inputs)

async def test_agent_trajectory_with_llm_judge():
    # 1) Initialize agent and evaluator
    agent = create_main_agent()
    trajectory_judge = create_trajectory_pipeline_judge()

    # 2) Pick a subset of queries for this test (random sample)
    random.seed(42)
    sample_queries = random.sample(TEST_QUERIES, k=min(5, len(TEST_QUERIES)))
    dataset_inputs = build_dataset_inputs(sample_queries)

    results = []
    for inp in dataset_inputs:
        # 3) Run agent to get full trajectory
        agent_result = await run_agent_on_input(agent, inp)
        outputs = agent_result["messages"]

        # 4) LLM-as-judge over trajectory
        evaluation = trajectory_judge(outputs=outputs)

        # evaluation has structure:
        # {
        #   "key": "trajectory_pipeline_quality",
        #   "score": 0 or 1,
        #   "comment": "...",
        #   "unnecessary_steps": [...],
        #   "failed_steps": [...],
        #   "unused_output_steps": [...]
        # }

        print("\n=== Query ===")
        print(inp["messages"][0].content)
        print("=== Judge Evaluation ===")
        print(evaluation)

        results.append(
            {
                "query": inp["messages"][0].content,
                "evaluation": evaluation,
            }
        )

    # 5) Basic assertion: no catastrophic failures on this sample
    # You can tighten this later.
    # For now, we just assert that evaluations ran and returned a key and score.
    assert len(results) > 0
    for r in results:
        ev = r["evaluation"]
        assert ev.get("key") == "trajectory_pipeline_quality"
        assert isinstance(ev.get("score"), int)

if __name__ == "__main__":
    asyncio.run(test_agent_trajectory_with_llm_judge())