"""
Layered test script for backend/core/tools/tcmb_data.py and the TCMB data agent.

Layers:
  1. get_tcmb_datagroup     — raw vector search on the datagroups collection
  2. get_tcmb_series_top_k  — raw vector search on the series collection with filter
  3. search_tcmb_series     — full hierarchical search tool (datagroups -> series)
  4. get_tcmb_data          — TCMB EVDS API fetch with a known serie code
  5. tcmb_data_agent        — full agent end-to-end with a natural language query

Run from the project root:
    python test_tcmb_agent.py
"""
import asyncio
import textwrap
from datetime import datetime

from backend.core.tools.tcmb_data import (
    get_tcmb_datagroup,
    get_tcmb_series_top_k,
    search_tcmb_series,
    get_tcmb_data,
)


DIVIDER = "-" * 70


def header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def section(label: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {label}")
    print(DIVIDER)


def print_result(result: object, indent: int = 2) -> None:
    if isinstance(result, str):
        wrapped = textwrap.indent(textwrap.fill(result, width=80), " " * indent)
        print(wrapped)
    elif isinstance(result, dict):
        for k, v in result.items():
            if k == "top_datagroups" or k == "top_series":
                print(f"{' ' * indent}{k}:")
                for item in v:
                    summary = {
                        ik: iv
                        for ik, iv in item.items()
                        if ik in (
                            "DATAGROUP_CODE", "DATAGROUP_NAME_ENG", "SERIE_CODE",
                            "score", "text", "START_DATE", "END_DATE",
                        )
                    }
                    print(f"{' ' * (indent + 2)}{summary}")
            else:
                val_str = str(v)[:200] + "..." if len(str(v)) > 200 else str(v)
                print(f"{' ' * indent}{k}: {val_str}")
    else:
        print(f"{' ' * indent}{result}")


async def test_layer_1(query: str) -> str | None:
    """Test get_tcmb_datagroup (raw vector search on datagroups)."""
    header("LAYER 1 — get_tcmb_datagroup (helper)")
    print(f"  Query: {query!r}")

    result = await get_tcmb_datagroup(query=query, k=3)
    print_result(result)

    if result.get("success"):
        codes = [dg.get("DATAGROUP_CODE") for dg in result.get("top_datagroups", [])]
        print(f"\n  Extracted codes: {codes}")
        return codes[0] if codes else None

    print(f"\n  FAILED: {result.get('error')}")
    return None


async def test_layer_2(query: str, datagroup_code: str | None) -> str | None:
    """Test get_tcmb_series_top_k (raw vector search on series with optional filter)."""
    header("LAYER 2 — get_tcmb_series_top_k (helper)")
    print(f"  Query: {query!r}")
    print(f"  Filter: datagroup_code={datagroup_code!r}")

    result = await get_tcmb_series_top_k(
        query=query,
        datagroup_codes=[datagroup_code] if datagroup_code else None,
        k=5,
    )
    print_result(result)

    if result.get("success"):
        best = result.get("best_serie", {})
        code = best.get("SERIE_CODE")
        print(f"\n  Best serie code: {code}")
        return code

    print(f"\n  FAILED: {result.get('error')}")
    return None


async def test_layer_3(query: str) -> str | None:
    """Test search_tcmb_series tool (hierarchical search: datagroups then series)."""
    header("LAYER 3 — search_tcmb_series (tool)")
    print(f"  Query: {query!r}")

    result = await search_tcmb_series.ainvoke({"query": query})
    print_result(result)

    # Extract a serie code from the output for use in layer 4
    serie_code = None
    if isinstance(result, str):
        for line in result.splitlines():
            if line.startswith("Serie Code:"):
                serie_code = line.split(":", 1)[1].strip()
                break

    print(f"\n  Extracted serie code for layer 4: {serie_code!r}")
    return serie_code


async def test_layer_4(serie_code: str | None) -> None:
    """Test get_tcmb_data tool (TCMB EVDS API fetch)."""
    header("LAYER 4 — get_tcmb_data (tool)")

    # Fall back to a well-known serie code if layer 3 did not return one
    code = serie_code or "TP.DK.USD.A.YTL"
    print(f"  Serie code: {code!r}")
    print(f"  Date range: 01-01-2023 to 01-01-2025")

    result = await get_tcmb_data.ainvoke(
        {
            "serie_codes": [code],
            "start_date": "01-01-2023",
            "end_date": "01-01-2025",
        }
    )
    print_result(result)


async def test_layer_5(query: str) -> None:
    """Test full tcmb_data_agent with a natural language query via ainvoke."""
    header("LAYER 5 — tcmb_data_agent (full agent)")
    print(f"  Query: {query!r}")

    # Import agent here to avoid heavy imports at module level
    from datetime import datetime
    from backend.core.prompts import tcmb_data_agent_prompt
    from backend.shared.constants import CURRENT_MODEL
    from langchain.agents import create_agent
    from backend.core.tools.tcmb_data import search_tcmb_series, get_tcmb_data

    agent = create_agent(
        model=CURRENT_MODEL,
        tools=[search_tcmb_series, get_tcmb_data],
        system_prompt=tcmb_data_agent_prompt.format(
            current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

    answer = None
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content:
            answer = msg.content
            break

    section("Agent final answer")
    print_result(answer or "(no answer)")


async def main() -> None:
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- Change these to explore different queries ---
    SEARCH_QUERY = "USD/TL exchange rate"
    AGENT_QUERY = (
        "Fetch the monthly USD/TL exchange rate for 2023 "
        "and summarise the trend."
    )
    # -------------------------------------------------

    # Layer 1 — raw datagroup search
    datagroup_code = await test_layer_1(SEARCH_QUERY)

    # Layer 2 — raw series search (uses the code found in layer 1)
    best_serie_code = await test_layer_2(SEARCH_QUERY, datagroup_code)

    # Layer 3 — combined hierarchical search tool
    tool_serie_code = await test_layer_3(SEARCH_QUERY)

    # Layer 4 — fetch actual data (uses layer 3 result, falls back to a known code)
    await test_layer_4(tool_serie_code or best_serie_code)

    # Layer 5 — full agent end-to-end
    await test_layer_5(AGENT_QUERY)

    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


if __name__ == "__main__":
    asyncio.run(main())
