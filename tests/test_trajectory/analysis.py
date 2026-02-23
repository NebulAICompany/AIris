# analysis.py
from collections import Counter
from typing import List, Dict, Any


def extract_steps_from_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    """
    LangChain mesajlarından (HumanMessage, AIMessage, ToolMessage vs.)
    analiz için kullanılabilir düz bir step listesi çıkarır.
    """
    steps: List[Dict[str, Any]] = []
    step_index = 0

    for msg in messages:
        msg_type = getattr(msg, "type", None) or getattr(msg, "_type", None)

        # Human
        if msg_type == "human":
            steps.append({
                "index": step_index,
                "kind": "human",
                "role": "user",
                "content": msg.content,
            })
            step_index += 1
            continue

        # AI
        if msg_type == "ai":
            tool_calls = getattr(msg, "tool_calls", None) or \
            msg.additional_kwargs.get("tool_calls", []) or []
            content = msg.content

            # LLM step
            steps.append({
                "index": step_index,
                "kind": "llm",
                "role": "ai",
                "content": content,
                "tool_calls": tool_calls,
            })
            step_index += 1

            # Tool calls as separate steps
            for tc in tool_calls:
                steps.append({
                    "index": step_index,
                    "kind": "tool_call",
                    "tool_name": tc.get("name"),
                    "tool_args": tc.get("args", {}),
                    "tool_id": tc.get("id"),
                })
                step_index += 1
            continue

        # Tool result (LangChain ToolMessage veya benzeri)
        if msg_type == "tool":
            steps.append({
                "index": step_index,
                "kind": "tool_result",
                "tool_name": getattr(msg, "name", None),
                "content": msg.content,
            })
            step_index += 1
            continue

        # Diğer tipler için sadece generic log
        steps.append({
            "index": step_index,
            "kind": msg_type or "unknown",
            "content": getattr(msg, "content", None),
        })
        step_index += 1

    return steps


def compute_tool_call_stats(steps: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Hangi tool kaç kere çağrılmış?
    """
    counter = Counter()
    for s in steps:
        if s.get("kind") == "tool_call":
            name = s.get("tool_name") or "UNKNOWN_TOOL"
            counter[name] += 1
    return dict(counter)


def find_redundant_pattern_comments(steps: List[Dict[str, Any]]) -> List[str]:
    """
    Basit tekrar / loop pattern yorumları üretir.
    Örn: x→y→x→y gibi patternleri işaretler, aynı tool'un çok çağrılması vs.
    """
    comments: List[str] = []

    # Tool call count
    stats = compute_tool_call_stats(steps)
    for tool, count in stats.items():
        if count > 1:
            comments.append(
                f"{tool} aracı toplam {count} kez çağrılmış. "
                "Bu tekrarların bazıları aynı amaca hizmet ediyor veya çıktıları kullanılmamış olabilir."
            )

    # Tool call sequence
    seq = [s["tool_name"] for s in steps if s.get("kind") == "tool_call"]

    # x→y→x→y türü pattern
    if len(seq) >= 4:
        for i in range(len(seq) - 3):
            a, b, c, d = seq[i:i+4]
            if a == c and b == d and a != b:
                comments.append(
                    f"Tool çağrı dizisinde {a}→{b}→{a}→{b} gibi bir tekrar pattern'i gözlenmiş. "
                    "Bu, gereksiz ileri-geri çağrılara işaret ediyor olabilir."
                )
                break

    return comments
