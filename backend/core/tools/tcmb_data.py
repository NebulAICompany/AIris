import asyncio
from typing import Any, Dict, List, Optional
import pandas as pd
from evds import evdsAPI
from langchain_core.tools import tool
from qdrant_client import models
from backend.retrieval.retriever import embed_query, get_or_load_vectorstore
from backend.shared.constants import TCMB_API_KEY
from backend.shared.logger import get_logger

logger = get_logger("TCMB_TOOLS")

async def get_tcmb_datagroup(
    query: str,
    k: int = 1,
    score_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """Searches the 'datagroups' vectorstore collection by vector similarity.

    Searches on the embedded datagroup name and note text. Returns the best match and its metadata.
    Payload structure stored by load_datagroup_vs.py:
    {"text": "DATAGROUP_NAME_ENG\\nNOTE_ENG", "metadata": {all fields except SERIES}}

    Args:
        query (str): The search query.
        k (int, optional): Number of top results to return. Defaults to 1.
        score_threshold (float, optional): Minimum similarity score threshold. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the search results.
            On success: {"success": True, "query": str, "best_score": float, "top_datagroups": List[Dict], ...best metadata}
            On failure: {"success": False, "error": str, "error_code": str}
    """
    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty.", "error_code": "EMPTY_QUERY"}

    try:
        logger.info(f"Searching datagroup for query: {query} (k={k})")

        client = await get_or_load_vectorstore()

        has_collection = await client.collection_exists(collection_name="datagroups")
        if not has_collection:
            return {
                "success": False,
                "error": "No vectorstore collection named 'datagroups' found.",
                "error_code": "NO_COLLECTION",
            }

        query_embedding = await asyncio.to_thread(embed_query, query)

        kwargs: Dict[str, Any] = dict(
            collection_name="datagroups",
            query=query_embedding,
            with_payload=True,
            limit=k,
        )
        if score_threshold is not None:
            kwargs["score_threshold"] = score_threshold

        response = await client.query_points(**kwargs)
        points = response.points if response is not None else []

        if not points:
            return {
                "success": False,
                "error": "No matching datagroup entries found in vectorstore.",
                "error_code": "NO_MATCH",
            }

        sorted_points = sorted(points, key=lambda p: float(p.score or 0.0), reverse=True)
        best_score = float(sorted_points[0].score or 0.0)

        top_datagroups: List[Dict[str, Any]] = []
        for p in sorted_points:
            payload = p.payload if isinstance(p.payload, dict) else {}
            meta = payload.get("metadata", {})
            top_datagroups.append({
                "score": float(p.score or 0.0),
                "text": payload.get("text", ""),
                **meta,
            })

        return {
            "success": True,
            "query": query,
            "best_score": best_score,
            "top_datagroups": top_datagroups,
            "message": "Most suitable datagroup(s) selected by vector similarity.",
        }

    except Exception as e:
        error_msg = f"Error while finding datagroup from vectorstore: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "error_code": "EXCEPTION"}


async def get_tcmb_series_top_k(
    query: str,
    datagroup_codes: Optional[List[str]] = None,
    k: int = 3,
    score_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """Searches the 'series' vectorstore collection by vector similarity.

    Searches on the embedded series text. When datagroup_codes is provided, the search is filtered
    to only series belonging to those datagroups (MatchAny), implementing the hierarchical retrieval step.
    Payload structure stored by load_datagroup_vs.py:
    {
        "text": "Series name: ...\\nFrequency: ...\\nDefault aggregation: ...",
        "metadata": {SERIE_CODE, SERIE_NAME, TAG, TAG_ENG, METADATA_LINK,
                     METADATA_LINK_ENG, START_DATE, END_DATE, DATAGROUP_CODE}
    }

    Args:
        query (str): The search query.
        datagroup_codes (List[str], optional): List of datagroup codes to filter by. Defaults to None.
        k (int, optional): Number of top results to return. Defaults to 3.
        score_threshold (float, optional): Minimum similarity score threshold. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the search results.
            On success: {"success": True, "query": str, "datagroup_codes": List[str], "best_score": float, "best_serie": Dict, "top_series": List[Dict]}
            On failure: {"success": False, "error": str, "error_code": str}
    """
    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty.", "error_code": "EMPTY_QUERY"}

    try:
        logger.info(
            f"Searching series for query: {query} "
            f"(datagroup_codes={datagroup_codes}, k={k})"
        )

        client = await get_or_load_vectorstore()

        has_collection = await client.collection_exists(collection_name="series")
        if not has_collection:
            return {
                "success": False,
                "error": "No vectorstore collection named 'series' found.",
                "error_code": "NO_COLLECTION",
            }

        query_filter = None
        if datagroup_codes:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.DATAGROUP_CODE",
                        match=models.MatchAny(any=datagroup_codes),
                    )
                ]
            )

        query_embedding = await asyncio.to_thread(embed_query, query)

        kwargs: Dict[str, Any] = dict(
            collection_name="series",
            query=query_embedding,
            with_payload=True,
            limit=k,
            query_filter=query_filter,
        )
        if score_threshold is not None:
            kwargs["score_threshold"] = score_threshold

        response = await client.query_points(**kwargs)
        points = response.points if response is not None else []

        if not points:
            return {
                "success": False,
                "error": "No matching series entries found in vectorstore.",
                "error_code": "NO_MATCH",
            }

        sorted_points = sorted(points, key=lambda p: float(p.score or 0.0), reverse=True)

        top_series: List[Dict[str, Any]] = []
        for p in sorted_points[:k]:
            payload = p.payload if isinstance(p.payload, dict) else {}
            meta = payload.get("metadata", {})
            top_series.append({
                "score": float(p.score or 0.0),
                "text": payload.get("text", ""),
                **meta,
            })

        best = top_series[0] if top_series else {}

        return {
            "success": True,
            "query": query,
            "datagroup_codes": datagroup_codes,
            "best_score": best.get("score", 0.0),
            "best_serie": best,
            "top_series": top_series,
            "message": "Top series selected by vector similarity.",
        }

    except Exception as e:
        error_msg = f"Error while finding series from vectorstore: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "error_code": "EXCEPTION"}


@tool(parse_docstring=True)
async def search_tcmb_series(
    query: str,
) -> str:
    """Find the most relevant TCMB EVDS series for a natural language query.

    Runs a two-stage hierarchical vector search:
    1. Finds the top data groups whose embedded name and description best match the query.
    2. Uses those data group codes as a filter and finds the top series within them whose embedded text best matches the query.

    Returns the best matching series with their codes and metadata. Pass the SERIE_CODE values from this result to get_tcmb_data to fetch actual observations.

    Args:
        query (str): Natural language description of the economic indicator you need (e.g. "USD exchange rate", "CPI inflation", "deposit money banks").

    Returns:
        str: Formatted string containing the matched series codes and descriptions, or an error message.
    """
    datagroup_result = await get_tcmb_datagroup(query=query, k=3)

    if not datagroup_result.get("success"):
        return f"Error finding data groups: {datagroup_result.get('error', 'Unknown error')}"

    datagroup_codes = [
        dg["DATAGROUP_CODE"]
        for dg in datagroup_result.get("top_datagroups", [])
        if dg.get("DATAGROUP_CODE")
    ]

    if not datagroup_codes:
        return "No data groups found for the given query."

    series_result = await get_tcmb_series_top_k(
        query=query,
        datagroup_codes=datagroup_codes,
        k=5,
    )

    if not series_result.get("success"):
        return f"Error finding series: {series_result.get('error', 'Unknown error')}"

    lines: List[str] = [
        f"Matched data groups: {', '.join(datagroup_codes)}",
        "",
    ]
    for serie in series_result.get("top_series", []):
        lines.append(
            f"Serie Code: {serie.get('SERIE_CODE', 'N/A')}\n"
            f"Description: {serie.get('text', 'N/A')}\n"
            f"Data group: {serie.get('DATAGROUP_CODE', 'N/A')}\n"
            f"Date range: {serie.get('START_DATE', '')} to {serie.get('END_DATE', '')}\n"
            f"Similarity score: {serie.get('score', 0.0):.4f}"
        )

    return "\n\n---\n\n".join(lines) if series_result.get("top_series") else "No series found."


@tool(parse_docstring=True)
async def get_tcmb_data(
    serie_codes: List[str],
    start_date: str,
    end_date: str,
    aggregation_method: Optional[str] = None,
    frequency: Optional[int] = None,
) -> str:
    """Fetch actual time-series observations from the TCMB EVDS API for one or more series.

    Returns all observations as a formatted table ready for analysis or charting.
    Call this after identifying the exact serie codes with search_tcmb_series.

    Args:
        serie_codes (List[str]): List of SERIE_CODE values to fetch (e.g. ["TP.ISTIRAKBS.A1", "TP.ISTIRAKBS.A2"]).
        start_date (str): Start date in DD-MM-YYYY format (e.g. "01-01-2020").
        end_date (str): End date in DD-MM-YYYY format (e.g. "01-01-2025").
        aggregation_method (str, optional): Optional aggregation override for all series. One of avg, min, max, first, last, sum. Defaults to None.
        frequency (int, optional): Optional frequency override. 1=daily, 2=workdaily, 3=weekly, 4=fortnightly, 5=monthly, 6=quarterly, 7=semiannual, 8=annual. Defaults to None.

    Returns:
        str: Formatted string containing the requested observations, or an error message.
    """
    if not serie_codes:
        return "Error: No serie codes provided."

    def _fetch() -> pd.DataFrame:
        evds = evdsAPI(TCMB_API_KEY)
        return evds.get_data(
            serie_codes,
            startdate=start_date,
            enddate=end_date,
            aggregation_types=aggregation_method or "",
            frequency=str(frequency) if frequency is not None else "",
        )

    try:
        logger.info(f"[TOOL] Fetching TCMB EVDS data for series: {serie_codes}")

        df: pd.DataFrame = await asyncio.to_thread(_fetch)

        if not isinstance(df, pd.DataFrame) or df.empty:
            return (
                f"No data returned from TCMB EVDS for series {serie_codes} "
                f"between {start_date} and {end_date}. "
                "The series may not have observations in this date range."
            )

        lines = [
            f"TCMB EVDS Data — Series: {', '.join(serie_codes)}",
            f"Date range: {start_date} to {end_date} | Total observations: {len(df)}",
            "",
            df.to_string(index=False),
        ]
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error fetching TCMB data: {str(e)}")
        return f"Error fetching TCMB data: {str(e)}"