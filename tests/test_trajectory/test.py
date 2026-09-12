# tests/test_trajectory_llm_judge.py
import sys
from pathlib import Path

# Add workspace root to Python path
workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

import asyncio
import random
from typing import List, Dict, Any

from langchain_core.messages import HumanMessage
from langsmith import Client

from backend.core.agents import create_main_agent
from judge import create_trajectory_pipeline_judge
from queries import TEST_QUERIES

# BURAYI EKLE:
from analysis import (
    extract_steps_from_messages,
    compute_tool_call_stats,
    find_redundant_pattern_comments,
)

client = Client()


def build_dataset_inputs(queries: List[str]) -> List[Dict[str, Any]]:
    return [{"messages": [HumanMessage(content=q)]} for q in queries]


async def run_agent_on_input(agent, inputs: Dict[str, Any]) -> Dict[str, Any]:
    return await agent.ainvoke(inputs)


async def test_agent_trajectory_with_llm_judge():
    agent = create_main_agent()
    trajectory_judge = create_trajectory_pipeline_judge()

    random.seed(42)
    sample_queries = random.sample(TEST_QUERIES, k=min(5, len(TEST_QUERIES)))
    dataset_inputs = build_dataset_inputs(sample_queries)

    results = []

    with open("metrics.txt", "w", encoding="utf-8") as metrics_file:
        metrics_file.write("=== Agent Trajectory Evaluation Results ===\n")
        metrics_file.write("=" * 80 + "\n\n")

        for idx, inp in enumerate(dataset_inputs, 1):
            # 1) Agent run
            agent_result = await run_agent_on_input(agent, inp)
            outputs = agent_result["messages"]

            # 2) ANALYSIS.PY: extract step list from messages
            steps = extract_steps_from_messages(outputs)

            # 3) TOOL STATS + PATTERN COMMENTS
            tool_stats = compute_tool_call_stats(steps)
            pattern_comments = find_redundant_pattern_comments(steps)

            # 4) LLM-as-judge
            evaluation = trajectory_judge(outputs=outputs)

            query_text = inp["messages"][0].content

            # Console output
            print(f"\n=== Query {idx} ===")
            print(query_text)

            print("\n--- Tool call statistics ---")
            print(tool_stats)

            print("\n--- Step by step flow ---")
            for s in steps:
                kind = s["kind"]
                if kind == "tool_call":
                    print(f"[{s['index']}] TOOL_CALL :: {s['tool_name']} args={s['tool_args']}")
                elif kind == "tool_result":
                    print(f"[{s['index']}] TOOL_RESULT :: {s['tool_name']} content={str(s['content'])[:120]}...")
                else:
                    print(f"[{s['index']}] {kind.upper()} :: {str(s.get('content'))[:120]}...")

            print("\n--- Heuristic pattern comments ---")
            for c in pattern_comments or ["No significant repetition / loop pattern detected."]:
                print("-", c)

            print("\n--- LLM Judge Evaluation ---")
            print(evaluation)

            # METRICS.TXT REPORT
            metrics_file.write(f"Query #{idx}\n")
            metrics_file.write("-" * 80 + "\n")
            metrics_file.write(f"Question: {query_text}\n\n")

            metrics_file.write("Tool call statistics:\n")
            for tool, count in tool_stats.items():
                metrics_file.write(f"  - {tool}: {count} calls\n")
            if not tool_stats:
                metrics_file.write("  - No tool calls.\n")
            metrics_file.write("\n")

            metrics_file.write("Step by step flow:\n")
            for s in steps:
                kind = s["kind"]
                if kind == "tool_call":
                    metrics_file.write(
                        f"  [{s['index']}] TOOL_CALL :: {s['tool_name']} args={s['tool_args']}\n"
                    )
                elif kind == "tool_result":
                    metrics_file.write(
                        f"  [{s['index']}] TOOL_RESULT :: {s['tool_name']} "
                        f"content={str(s['content'])[:200]}...\n"
                    )
                else:
                    metrics_file.write(
                        f"  [{s['index']}] {kind.upper()} :: {str(s.get('content'))[:200]}...\n"
                    )
            metrics_file.write("\n")

            metrics_file.write("Heuristic pattern comments:\n")
            if pattern_comments:
                for c in pattern_comments:
                    metrics_file.write(f"  - {c}\n")
            else:
                metrics_file.write("  - No significant repetition / loop pattern detected.\n")
            metrics_file.write("\n")

            metrics_file.write("LLM Judge evaluation:\n")
            metrics_file.write(f"  Score: {evaluation.get('score')}\n")
            metrics_file.write(
                f"  Reasoning: {evaluation.get('reasoning', evaluation.get('comment', 'N/A'))}\n"
            )
            metrics_file.write("\n" + "=" * 80 + "\n\n")
            metrics_file.flush()

            results.append(
                {
                    "query": query_text,
                    "evaluation": evaluation,
                    "tool_stats": tool_stats,
                    "steps": steps,
                }
            )

    # Simple assertion (for judge JSON)
    assert len(results) > 0
    for r in results:
        ev = r["evaluation"]
        assert isinstance(ev.get("score"), int)
        assert ev.get("score") in [0, 1]

if __name__ == "__main__":
    asyncio.run(test_agent_trajectory_with_llm_judge())