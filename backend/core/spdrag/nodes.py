import asyncio
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import tiktoken
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command
from pydantic import BaseModel, Field
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from backend.core.spdrag.prompts import (
    LEAD_RESEARCHER_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    SYNTHESIS_PROMPT,
)
from backend.core.spdrag.state import (
    AgentAction,
    AgentState,
    SubAgentInput,
    Summary,
    TodoItem,
)
from backend.core.tools.rag import search_specific_document_for_research
from backend.pipeline.vector import generate_embeddings
from backend.shared.constants import (
    RESEARCH_LLM_FAST,
    RESEARCH_LLM_REASONING,
    get_synthesizer_token_limit_for_fast,
)
from backend.shared.logger import get_logger

logger = get_logger("SPDRAG")

_ENCODER: Optional[tiktoken.Encoding] = None


def _get_encoder() -> tiktoken.Encoding:
    """Lazily initialize and return a shared tiktoken encoder."""
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def _estimate_tokens(text: str) -> int:
    """Estimate token count using cl100k_base tokenizer."""
    if not text:
        return 0
    return len(_get_encoder().encode(text))


def _group_by_tokens(
    texts: List[str], children: np.ndarray, target_tokens: int
) -> List[List[str]]:
    """Group texts into batches that respect the clustering hierarchy and token budget.

    Traverses the UPGMA merge history (children_) from AgglomerativeClustering to form
    the largest possible clusters whose combined token count does not exceed
    target_tokens, preserving similarity-ordered batching for the synthesis layer.

    Args:
        texts: List of text chunks (e.g. sub-agent findings) to batch.
        children: (N-1, 2) array of merge indices from sklearn AgglomerativeClustering.children_.
        target_tokens: Maximum tokens per batch (typically from synthesizer context limit).

    Returns:
        List of batches; each batch is a list of strings to be summarized together.
    """
    n_samples = len(texts)
    node_tokens = {i: _estimate_tokens(texts[i]) for i in range(n_samples)}
    node_indices = {i: [i] for i in range(n_samples)}
    valid_roots = set(range(n_samples))
    valid_nodes = set(range(n_samples))

    for idx, (c1, c2) in enumerate(children):
        new_node = n_samples + idx
        c1, c2 = int(c1), int(c2)
        is_merge_possible = (c1 in valid_nodes) and (c2 in valid_nodes)

        if is_merge_possible:
            combined_tokens = node_tokens[c1] + node_tokens[c2]
            if combined_tokens <= target_tokens:
                valid_nodes.add(new_node)
                node_tokens[new_node] = combined_tokens
                node_indices[new_node] = node_indices[c1] + node_indices[c2]

                if c1 in valid_roots:
                    valid_roots.remove(c1)
                if c2 in valid_roots:
                    valid_roots.remove(c2)
                valid_roots.add(new_node)

    batches = []
    for root in valid_roots:
        indices = node_indices[root]
        batches.append([texts[i] for i in indices])
    return batches


async def _summarize_batch_findings(
    findings_batch: List[str],
    root_query: str,
    synthesis_directive: str = "",
) -> str:
    """Summarize one findings batch into a merged summary."""
    batch_text = "\n\n---\n\n".join(findings_batch)
    prompt_content = SYNTHESIS_PROMPT.format(
        findings=batch_text,
        query=root_query,
        synthesis_directive=synthesis_directive,
    )
    response = await RESEARCH_LLM_REASONING.ainvoke([HumanMessage(content=prompt_content)])
    return getattr(response, "content", str(response))


async def recursive_summarize_findings(
    raw_findings: List[str],
    root_query: str,
    target_batch_tokens: Optional[int] = None,
    synthesis_directive: str = "",
) -> str:
    """Recursively summarize findings using agglomerative clustering."""
    if target_batch_tokens is None:
        target_batch_tokens = get_synthesizer_token_limit_for_fast()

    current_level: List[str] = list(raw_findings)
    iteration = 0

    while len(current_level) > 1:
        iteration += 1
        n = len(current_level)
        logger.info(
            "Recursive summarization iteration %s, %s chunk(s) remaining",
            iteration,
            n,
        )

        embeddings = np.array(await generate_embeddings(current_level), dtype=np.float32)
        sim_matrix = cosine_similarity(embeddings)
        dist_matrix = 1.0 - sim_matrix
        np.fill_diagonal(dist_matrix, 0)
        dist_matrix[dist_matrix < 0] = 0

        clustering = AgglomerativeClustering(
            n_clusters=1, linkage="average", metric="precomputed"
        ).fit(dist_matrix)

        batches = _group_by_tokens(
            current_level, clustering.children_, target_batch_tokens
        )

        # Ensure convergence even if clustering did not reduce batch count.
        if len(batches) >= n:
            batches = [current_level]

        logger.info("Formed %s batch(es) for LLM synthesis", len(batches))

        tasks = [
            _summarize_batch_findings(
                batch,
                root_query=root_query,
                synthesis_directive=synthesis_directive,
            )
            for batch in batches
            if batch
        ]
        current_level = list(await asyncio.gather(*tasks))

    return current_level[0]


class WriteTodos(BaseModel):
    """Structured output from coordination layer to drive retrieval+synthesis."""

    sub_agent_todos: List[TodoItem] = Field(
        description=(
            "Shared Instruction Set for all sub-agents. Each todo must include task "
            "and status."
        )
    )
    synthesis_directive: str = Field(
        description="Guidance for synthesizer goal, priorities, and output structure."
    )


async def orchestrator_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Coordination layer: decompose query into sub-agent todos and directive."""
    del config
    messages = state["messages"]

    todo_writer = RESEARCH_LLM_REASONING.with_structured_output(
        WriteTodos, method="function_calling", include_raw=False
    )
    result = await todo_writer.ainvoke(
        [{"role": "system", "content": LEAD_RESEARCHER_PROMPT}] + messages
    )

    logger.info("Synthesis directive created: %s", result.synthesis_directive)
    logger.info("Generated %s sub-agent todo(s)", len(result.sub_agent_todos))

    return {
        "messages": [
            AIMessage(
                content=f"Prepared {len(result.sub_agent_todos)} research task(s) for sub-agents."
            )
        ],
        "sub_agent_todos": result.sub_agent_todos,
        "synthesis_directive": result.synthesis_directive,
    }


async def document_sub_agent_node(input_data: SubAgentInput) -> Dict[str, Any]:
    """Parallel retrieval layer: iterative document-scoped retrieval loop."""
    safety_limit = 5
    doc_name = input_data["document_name"]
    todos_list = input_data.get("todos", [])

    todos_str = (
        "\n".join(f"{i + 1}. {t.task}" for i, t in enumerate(todos_list))
        if todos_list
        else "No specific sub-tasks provided."
    )

    system_prompt = RESEARCH_SYSTEM_PROMPT.format(file_name=doc_name)
    messages: List = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"**Orchestrator Assigned Tasks**:\n{todos_str}\n\n"
                "Begin your investigation. Issue SEARCH actions to retrieve "
                "information, then FINALIZE once all tasks are covered."
            )
        ),
    ]

    action_extractor = RESEARCH_LLM_FAST.with_structured_output(
        AgentAction, method="function_calling", include_raw=False
    )

    iteration = 0
    while True:
        iteration += 1

        if iteration > safety_limit:
            logger.error(
                "[%s] Safety ceiling of %s iterations reached; forcing extraction.",
                doc_name,
                safety_limit,
            )
            messages.append(
                HumanMessage(
                    content="You have used the maximum number of searches. You MUST finalize your findings now."
                )
            )
            try:
                action = await action_extractor.ainvoke(messages)
                findings = action.findings or "Safety limit reached; partial findings only."
            except Exception as exc:
                logger.error("[%s] Forced finalization failed: %s", doc_name, exc)
                findings = "Extraction failed after safety limit."
            return {"global_context": [Summary(document_name=doc_name, findings=findings)]}

        try:
            action: AgentAction = await action_extractor.ainvoke(messages)
        except Exception as exc:
            logger.error(
                "[%s] AgentAction parsing failed (iter %s): %s; aborting loop.",
                doc_name,
                iteration,
                exc,
            )
            return {
                "global_context": [
                    Summary(
                        document_name=doc_name,
                        findings="Action parsing failed; no findings extracted.",
                    )
                ]
            }

        logger.info(
            "[%s] Iter %s action=%s reasoning=%s",
            doc_name,
            iteration,
            action.action,
            action.reasoning,
        )

        if action.action == "finalize":
            if not action.findings:
                logger.warning(
                    "[%s] Sub-agent finalized with empty findings (iter %s).",
                    doc_name,
                    iteration,
                )
            return {
                "global_context": [
                    Summary(
                        document_name=doc_name,
                        findings=action.findings or "No findings extracted.",
                    )
                ]
            }

        if not action.query:
            logger.warning(
                "[%s] Sub-agent issued search with no query (iter %s).",
                doc_name,
                iteration,
            )
            messages.append(
                HumanMessage(
                    content=(
                        "Your last action was 'search' but the `query` field was empty. "
                        "Please provide a specific search string, or finalize if you have gathered enough information."
                    )
                )
            )
            continue

        search_results = await search_specific_document_for_research.ainvoke(
            {"query": action.query, "file_name": doc_name}
        )
        logger.info("[%s] Search query: %s", doc_name, action.query)

        messages.append(
            AIMessage(content=f"[SEARCH] Reasoning: {action.reasoning}\nQuery: {action.query}")
        )
        messages.append(
            HumanMessage(content=f"Search results for '{action.query}':\n\n{search_results}")
        )


async def synthesis_node(
    state: AgentState, config: RunnableConfig
) -> Command[Literal[END]]:
    """Synthesis layer: merge all document summaries into final response."""
    del config
    global_context = state.get("global_context", [])
    synthesis_directive = state.get("synthesis_directive", "")

    root_query = ""
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            root_query = getattr(msg, "content", "")
            break

    if global_context:
        raw_findings_chunks: List[str] = [
            f"Document: {summary.document_name}\nFindings:\n{summary.findings}"
            for summary in global_context
        ]
        merged_findings = await recursive_summarize_findings(
            raw_findings_chunks,
            root_query=root_query,
            synthesis_directive=synthesis_directive,
        )
    else:
        merged_findings = "No document findings available."

    return Command(goto=END, update={"messages": [AIMessage(content=merged_findings)]})
