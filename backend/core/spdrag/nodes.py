from datetime import datetime
import asyncio
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import tiktoken
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command
from pydantic import BaseModel, Field

from backend.core.spdrag.prompts import (
    CLARIFY_WITH_USER_INSTRUCTIONS,
    LEAD_RESEARCHER_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    SYNTHESIS_PROMPT,
    TRANSFORM_MESSAGES_INTO_PLAN_PROMPT,
)
from backend.core.spdrag.state import (
    AgentAction,
    AgentState,
    Plan,
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


def get_today_str() -> str:
    """Returns today's date as a formatted string (YYYY-MM-DD)."""
    return datetime.now().strftime("%Y-%m-%d")


def _get_encoder() -> tiktoken.Encoding:
    """Lazily initialise and return a shared tiktoken encoder.

    Uses cl100k_base, which is compatible with GPT-4/4.1/4o/5-style models
    and already used elsewhere in this project for accurate token counting.
    """
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def _estimate_tokens(text: str) -> int:
    """Estimate token count using the cl100k_base tokenizer."""
    if not text:
        return 0
    return len(_get_encoder().encode(text))


def _group_by_tokens(
    texts: List[str], children: np.ndarray, target_tokens: int
) -> List[List[str]]:
    """Group texts into batches using the agglomerative clustering tree.

    Traverses the merge history (children_) to identify the largest possible
    clusters that satisfy the target_tokens constraint.

    Args:
        texts: List of original text chunks.
        children: (N-1, 2) array of merge operations from AgglomerativeClustering.
        target_tokens: Max token budget per batch.

    Returns:
        List of batches (each batch is a list of strings).
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
        batch_texts = [texts[i] for i in indices]
        batches.append(batch_texts)

    return batches


async def _summarize_batch_findings(
    findings_batch: List[str],
    root_query: str,
    synthesis_directive: str = "",
) -> str:
    """Summarize a batch of findings into a single merged summary."""
    batch_text = "\n\n---\n\n".join(findings_batch)
    prompt_content = SYNTHESIS_PROMPT.format(
        findings=batch_text,
        query=root_query,
        synthesis_directive=synthesis_directive,
    )

    response = await RESEARCH_LLM_REASONING.ainvoke(
        [HumanMessage(content=prompt_content)]
    )
    return getattr(response, "content", str(response))


async def recursive_summarize_findings(
    raw_findings: List[str],
    root_query: str,
    target_batch_tokens: Optional[int] = None,
    synthesis_directive: str = "",
) -> str:
    """Hybrid Similarity-Ordered Recursive Summarization.

    Uses sklearn to perform agglomerative clustering on embeddings, then groups
    chunks into maximally-sized batches that respect the similarity hierarchy.
    """
    if target_batch_tokens is None:
        synth_limit = get_synthesizer_token_limit_for_fast()
        target_batch_tokens = synth_limit

    current_level: List[str] = list(raw_findings)
    iteration = 0

    while len(current_level) > 1:
        iteration += 1
        n = len(current_level)
        logger.info(
            f"Recursive summarization – iteration {iteration}, "
            f"{n} chunk(s) remaining"
        )

        embeddings = np.array(
            await generate_embeddings(current_level), dtype=np.float32
        )

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

        # If no reduction occurred, force a single batch to guarantee convergence
        if len(batches) >= n:
            batches = [current_level]

        logger.info(f"Formed {len(batches)} batch(es) for LLM synthesis")

        tasks = [
            _summarize_batch_findings(
                batch,
                root_query=root_query,
                synthesis_directive=synthesis_directive,
            )
            for batch in batches
            if batch
        ]
        next_level = await asyncio.gather(*tasks)
        current_level = list(next_level)

    return current_level[0]


def format_todos_as_string(todos: List[TodoItem]) -> str:
    """Formats a list of TodoItems as a readable string for prompts."""
    if not todos:
        return "No tasks defined yet."
    return "\n".join([f"- {t.task} [{t.status}]" for t in todos])


class AmbiguityCheck(BaseModel):
    """Model for structured output from ambiguity check."""

    is_ambiguous: bool = Field(
        description="True if the user request is vague or needs clarification"
    )
    clarifying_question: str = Field(
        description="The question to ask the user if ambiguous, else empty string"
    )


class WriteTodos(BaseModel):
    """Structured output schema for the orchestrator to define tasks for sub-agents."""

    sub_agent_todos: List[TodoItem] = Field(
        description="A list of specific tasks that EVERY sub-agent must execute for their assigned document. Each item must have a 'task' and a 'status' (default 'pending')."
    )
    synthesis_directive: str = Field(
        description=(
            "A concise instruction (2-4 sentences) for the downstream synthesizer: the main goal, what to prioritize, and how to structure the merged output."
        )
    )


class PlanApprovalCheck(BaseModel):
    """Model for structured output to detect plan approval from user messages."""

    is_approved: bool = Field(
        description="True if the user has approved the plan (e.g., 'yes', 'looks good', 'proceed', 'that's great')"
    )
    wants_changes: bool = Field(description="True if the user wants to modify the plan")
    feedback: str = Field(
        description="The user's feedback or requested changes if any, else empty string"
    )


async def clarify_intent_node(
    state: AgentState, config: RunnableConfig
) -> Command[Literal["generate_plan_node", END]]:
    """
    Analyzes the user's message to determine if clarification is needed.

    If the query is ambiguous, pauses execution (END) and sends a clarifying
    question to the user. Otherwise, proceeds to the planning phase.

    Args:
        state: Current agent state containing messages.
        config: Runtime configuration.

    Returns:
        Command routing to either END (wait for user) or generate_plan_node.
    """
    messages = state["messages"]
    selected_docs = state.get("selected_documents", [])

    # Build file context info
    file_context = ""
    if selected_docs:
        file_names = [doc.split("/")[-1].split("\\")[-1] for doc in selected_docs]
        file_context = f"\n\n**Available Files:** The user has already selected these files for analysis: {', '.join(file_names)}. Do NOT ask for files - they are already available."

    checker = RESEARCH_LLM_REASONING.with_structured_output(AmbiguityCheck)
    prompt_content = (
        CLARIFY_WITH_USER_INSTRUCTIONS.format(
            messages=get_buffer_string(messages), date=get_today_str()
        )
        + file_context
    )

    result = await checker.ainvoke([HumanMessage(content=prompt_content)])

    if result.is_ambiguous:
        return Command(
            goto=END,
            update={
                "is_ambiguous": True,
                "messages": [AIMessage(content=result.clarifying_question)],
            },
        )

    return Command(goto="generate_plan_node", update={"is_ambiguous": False})


async def generate_plan_node(
    state: AgentState, config: RunnableConfig
) -> Command[Literal["human_approval_node"]]:
    """
    Generates a strategic plan based on the user's request.

    Creates a Plan with strategy, steps (TodoItems), and reasoning.
    Outputs a user-facing summary for approval.

    Args:
        state: Current agent state containing messages.
        config: Runtime configuration.

    Returns:
        Command routing to human_approval_node with plan in state.
    """
    messages = state["messages"]
    selected_docs = state.get("selected_documents", [])

    # Build file context info
    file_context = ""
    if selected_docs:
        file_names = [doc.split("/")[-1].split("\\")[-1] for doc in selected_docs]
        file_context = f"\n\n**Available Files for Analysis:** {', '.join(file_names)}. Include steps to analyze these documents in your plan."

    planner = RESEARCH_LLM_REASONING.with_structured_output(Plan)
    prompt_content = (
        TRANSFORM_MESSAGES_INTO_PLAN_PROMPT.format(
            messages=get_buffer_string(messages), date=get_today_str()
        )
        + file_context
    )

    plan = await planner.ainvoke([HumanMessage(content=prompt_content)])

    # Format plan summary for user approval
    steps_str = "\n".join([f"- {step.task}" for step in plan.steps])
    plan_summary_msg = (
        f"**Proposed Plan:**\n"
        f"**Strategy:** {plan.strategy}\n\n"
        f"**Steps:**\n{steps_str}\n\n"
        f"**Reasoning:** {plan.reasoning}\n\n"
        f"Do you approve this plan? (yes/no)"
    )

    return Command(
        goto="human_approval_node",
        update={
            "plan": plan,
            "todo_queue": plan.steps,
            "messages": [AIMessage(content=plan_summary_msg)],
            "human_approval_status": "pending",
        },
    )


async def human_approval_node(
    state: AgentState, config: RunnableConfig
) -> Command[Literal["orchestrator_node", "generate_plan_node", END]]:
    """
    Uses LLM to analyze user's response to determine plan approval.

    This node uses conversation-based approval detection:
    - If user approves (says things like 'yes', 'proceed', 'looks good'), routes to orchestrator
    - If user wants changes, routes back to planning with feedback
    - If this is the first time showing the plan (no user response yet), waits for input

    Args:
        state: Current agent state.
        config: Runtime configuration.

    Returns:
        Command routing based on LLM's analysis of user's approval status.
    """
    messages = state.get("messages", [])
    approval_status = state.get("human_approval_status", "pending")

    # If plan was just generated and we haven't waited for user input yet,
    # end and wait for the user's response
    if approval_status == "pending":
        return Command(goto=END, update={"human_approval_status": "awaiting_feedback"})

    # We have user feedback - use LLM to analyze if they approved
    checker = RESEARCH_LLM_FAST.with_structured_output(PlanApprovalCheck)

    # Get the last few messages for context
    recent_messages = messages[-4:] if len(messages) > 4 else messages
    messages_str = get_buffer_string(recent_messages)

    prompt = f"""Analyze the following conversation to determine if the user has approved the proposed plan.

Conversation:
{messages_str}

Determine:
1. Has the user approved the plan? (e.g., 'yes', 'proceed', 'looks good', 'that's great', 'go ahead')
2. Does the user want to make changes to the plan?
3. What feedback or changes did they request (if any)?
"""

    result = await checker.ainvoke([HumanMessage(content=prompt)])

    if result.is_approved and not result.wants_changes:
        return Command(
            goto="orchestrator_node", update={"human_approval_status": "approved"}
        )

    if result.wants_changes:
        return Command(
            goto="generate_plan_node",
            update={
                "human_approval_status": "pending",
                "messages": [HumanMessage(content=f"User feedback: {result.feedback}")],
            },
        )

    # User hasn't clearly approved or rejected - ask for clarification
    return Command(
        goto=END,
        update={
            "human_approval_status": "awaiting_feedback",
            "messages": [
                AIMessage(
                    content="I've proposed a plan above. Would you like me to proceed with this plan, or would you like to make any changes?"
                )
            ],
        },
    )


async def orchestrator_node(
    state: AgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Defines tasks for sub-agents based on the user query.

    Uses structured output (no tool binding) so the LLM always returns a
    well-formed WriteTodos object deterministically.

    Args:
        state: Current agent state.
        config: Runtime configuration.

    Returns:
        State updates including messages and sub_agent_todos.
    """
    messages = state["messages"]

    todo_writer = RESEARCH_LLM_REASONING.with_structured_output(
        WriteTodos,
        method="function_calling",
        include_raw=False,
    )

    result = await todo_writer.ainvoke(
        [{"role": "system", "content": LEAD_RESEARCHER_PROMPT}] + messages
    )

    logger.info(f"SYNTHESIS DIRECTIVE created: {result.synthesis_directive}")
    logger.info(f"Generated {len(result.sub_agent_todos)} sub-agent todos")

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
    """
    Processes a document using an RLM-inspired iterative retrieval loop.

    The LLM fully controls iteration: it outputs a structured AgentAction each
    turn. The external loop executes the search and feeds results back, or exits
    when the LLM signals action="finalize". No tools are ever bound to the LLM.

    A high safety ceiling (SAFETY_LIMIT) exists only as an emergency fallback to
    prevent runaway costs — the LLM is expected to finalize well before it.

    Args:
        input_data: SubAgentInput containing the document_name and assigned todos.

    Returns:
        State update with the Summary added to global_context.
    """
    SAFETY_LIMIT = 5

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
                f"Begin your investigation. Issue SEARCH actions to retrieve "
                f"information, then FINALIZE once all tasks are covered."
            )
        ),
    ]

    action_extractor = RESEARCH_LLM_FAST.with_structured_output(
        AgentAction,
        method="function_calling",
        include_raw=False,
    )

    iteration = 0
    while True:
        iteration += 1

        if iteration > SAFETY_LIMIT:
            logger.error(
                f"[{doc_name}] Safety ceiling of {SAFETY_LIMIT} iterations reached — "
                f"LLM never issued 'finalize'. Forcing extraction."
            )
            messages.append(
                HumanMessage(
                    content="You have used the maximum number of searches. "
                    "You MUST finalize your findings now."
                )
            )
            try:
                action = await action_extractor.ainvoke(messages)
                findings = (
                    action.findings or "Safety limit reached; partial findings only."
                )
            except Exception as e:
                logger.error(f"[{doc_name}] Forced finalization failed: {e}")
                findings = "Extraction failed after safety limit."
            return {
                "global_context": [Summary(document_name=doc_name, findings=findings)]
            }

        try:
            action: AgentAction = await action_extractor.ainvoke(messages)
        except Exception as e:
            logger.error(
                f"[{doc_name}] AgentAction parsing failed (iter {iteration}): {e}. "
                f"Aborting loop."
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
            f"[{doc_name}] Iter {iteration} — "
            f"action={action.action!r} | reasoning={action.reasoning!r}"
        )

        if action.action == "finalize":
            if not action.findings:
                logger.warning(
                    f"[{doc_name}] LLM finalized with empty findings (iter {iteration})."
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
                f"[{doc_name}] LLM issued 'search' with no query (iter {iteration})."
            )
            messages.append(
                HumanMessage(
                    content="Your last action was 'search' but the `query` field was "
                    "empty. Please provide a specific search string, or finalize if "
                    "you have gathered enough information."
                )
            )
            continue

        search_results = await search_specific_document_for_research.ainvoke(
            {"query": action.query, "file_name": doc_name}
        )
        logger.info(f"[{doc_name}] Search query: '{action.query}'")

        messages.append(
            AIMessage(
                content=f"[SEARCH] Reasoning: {action.reasoning}\nQuery: {action.query}"
            )
        )
        messages.append(
            HumanMessage(
                content=f"Search results for '{action.query}':\n\n{search_results}"
            )
        )


async def synthesis_node(
    state: AgentState, config: RunnableConfig
) -> Command[Literal[END]]:
    """
    Aggregates all research findings and generates the final report.

    Combines summaries from global_context into a comprehensive response.

    Args:
        state: Current agent state with global_context populated.
        config: Runtime configuration.

    Returns:
        Command routing to END with final report in messages.
    """
    global_context = state.get("global_context", [])
    synthesis_directive = state.get("synthesis_directive", "")

    root_query = ""
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            root_query = getattr(msg, "content", "")
            break

    if global_context:
        raw_findings_chunks: List[str] = [
            f"Document: {s.document_name}\nFindings:\n{s.findings}"
            for s in global_context
        ]

        merged_findings = await recursive_summarize_findings(
            raw_findings_chunks,
            root_query=root_query,
            synthesis_directive=synthesis_directive,
        )
    else:
        merged_findings = "No document findings available."

    response = AIMessage(content=merged_findings)

    return Command(goto=END, update={"messages": [response]})


async def summarize_conversation_node(
    state: AgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Summarizes the conversation history if it exceeds a certain length.

    Args:
        state: Current agent state.
        config: Runtime configuration.

    Returns:
        State updates with new summary and removal commands for old messages.
    """
    messages = state.get("messages", [])

    # Check if we have enough messages to warrant summarization.
    # We keep the last 4 messages to preserve immediate context for the next steps.
    if len(messages) > 6:
        summary = state.get("summary", "")

        # Create summarization prompt.
        if summary:
            summary_message = (
                f"This is a summary of the conversation to date: {summary}\n\n"
                "Extend the summary by taking into account the new messages above:"
            )
        else:
            summary_message = "Create a summary of the conversation above:"

        # We summarize the messages that we are about to remove.
        messages_to_summarize = messages[:-4]

        prompt_messages = messages_to_summarize + [HumanMessage(content=summary_message)]
        response = await RESEARCH_LLM_FAST.ainvoke(prompt_messages)

        # Create RemoveMessage commands for the messages we summarized.
        delete_messages = [RemoveMessage(id=m.id) for m in messages_to_summarize]

        return {"summary": response.content, "messages": delete_messages}

    return {}
