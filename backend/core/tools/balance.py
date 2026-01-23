from datetime import date, datetime
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool
from backend.core.runner import generate_answer
from backend.pipeline.upload import parse_document
from backend.shared.constants import (
    BALANCE_TRANSACTION_CATEGORIES,
    BALANCE_TRANSACTION_CATEGORY_ALIASES,
)
from backend.shared.logger import get_logger
from backend.utils.balance_payments_database import (
    BalanceTransaction,
    balance_payments_db,
)
from backend.core.prompts import balance_of_payments_agent_prompt
from backend.shared.constants import OPENAI_MODEL
from langchain.agents import create_agent

logger = get_logger("BALANCE_TOOLS")


VALID_TRANSACTION_CATEGORIES = set(BALANCE_TRANSACTION_CATEGORIES)
ALIAS_LOOKUP = {
    key.lower(): value for key, value in BALANCE_TRANSACTION_CATEGORY_ALIASES.items()
}


def _normalize_category(raw_category: Optional[str]) -> str:
    """Validate that the provided category matches the supported subset."""

    if raw_category is None:
        raise ValueError(
            "Category is required. Choose one of: "
            + ", ".join(BALANCE_TRANSACTION_CATEGORIES)
        )

    cleaned = raw_category.strip()
    if not cleaned:
        raise ValueError(
            "Category cannot be empty. Choose one of: "
            + ", ".join(BALANCE_TRANSACTION_CATEGORIES)
        )

    candidates: List[str] = [cleaned]

    # If the value includes paired translations like "Operating (...)" or "(...)",
    # examine both the outer and inner segments.
    if "(" in cleaned and ")" in cleaned:
        start = cleaned.find("(")
        end = cleaned.rfind(")")
        if start != -1 and end != -1 and end > start:
            outside = cleaned[:start].strip()
            inside = cleaned[start + 1 : end].strip()
            if outside:
                candidates.append(outside)
            if inside:
                candidates.append(inside)

    # Also consider segments separated by common delimiters.
    for delimiter in ("/", "-", ","):
        if delimiter in cleaned:
            parts = [part.strip() for part in cleaned.split(delimiter)]
            candidates.extend(part for part in parts if part)

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        if candidate in VALID_TRANSACTION_CATEGORIES:
            return candidate

        alias_match = ALIAS_LOOKUP.get(candidate.lower())
        if alias_match:
            return alias_match

    raise ValueError(
        f"Invalid category '{raw_category}'. Choose one of: "
        + ", ".join(BALANCE_TRANSACTION_CATEGORIES)
    )


def _normalize_transaction_date(raw_date: Optional[str]) -> str:
    """Validate and normalize incoming transaction date strings."""

    if raw_date is None:
        return date.today().isoformat()

    cleaned = raw_date.strip()
    if not cleaned:
        return date.today().isoformat()

    # Accept a few common ledger date formats in addition to ISO.
    candidate_formats = [
        "%Y-%m-%d",           # ISO format
        "%Y-%m-%d %H:%M:%S",  # ISO with time (from Excel)
        "%d.%m.%Y",           # Turkish format
        "%d/%m/%Y",           # Common format
        "%d-%m-%Y",           # Dash separated
        "%m/%d/%Y",           # US format
        "%Y/%m/%d",           # Alternative ISO
    ]

    for fmt in candidate_formats:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue

    # Finally, try Python's flexible ISO parser.
    try:
        return datetime.fromisoformat(cleaned).date().isoformat()
    except ValueError as exc:
        logger.warning("Received unrecognized transaction date format: {}", cleaned)
        raise ValueError(
            "Invalid transaction_date. Use ISO format YYYY-MM-DD."
        ) from exc


def _store_transactions(transactions: List[BalanceTransaction]) -> str:
    try:
        stored = balance_payments_db.store_transactions(
            transactions=transactions,
        )

        categories = sorted({tx.category for tx in transactions if tx.category})
        if stored == 0:
            return "No transactions stored."

        if len(transactions) == 1 and categories:
            return f"Stored {stored} transaction categorized as {categories[0]}."

        if categories:
            category_summary = ", ".join(categories)
            return f"Stored {stored} transaction(s) spanning categories: {category_summary}."

        return f"Stored {stored} transaction(s)."
    except Exception as exc:
        logger.error("Failed to store balance transaction: {}", exc)
        return f"Error while storing transaction: {exc}"


@tool
def add_income_transaction(
    amount: float,
    category: str,
    transaction_date: Optional[str] = None,
) -> str:
    """Persist an income entry with categorized metadata."""

    if amount is None or amount <= 0:
        return "Amount must be a positive number."

    try:
        normalized_date = _normalize_transaction_date(transaction_date)
    except ValueError as exc:
        logger.warning("Income transaction rejected due to invalid date: {}", exc)
        return str(exc)

    try:
        normalized_category = _normalize_category(category)
    except ValueError as exc:
        logger.warning(
            "Income transaction rejected due to invalid category '{}': {}",
            category,
            exc,
        )
        return str(exc)

    transaction = BalanceTransaction(
        transaction_date=normalized_date,
        amount=float(amount),
        direction="income",
        category=normalized_category,
    )
    return _store_transactions([transaction])


@tool
def add_expense_transaction(
    amount: float,
    category: str,
    transaction_date: Optional[str] = None,
) -> str:
    """Persist an expense entry with categorized metadata."""

    if amount is None or amount <= 0:
        return "Amount must be a positive number."

    try:
        normalized_date = _normalize_transaction_date(transaction_date)
    except ValueError as exc:
        logger.warning("Expense transaction rejected due to invalid date: {}", exc)
        return str(exc)

    try:
        normalized_category = _normalize_category(category)
    except ValueError as exc:
        logger.warning(
            "Expense transaction rejected due to invalid category '{}': {}",
            category,
            exc,
        )
        return str(exc)

    transaction = BalanceTransaction(
        transaction_date=normalized_date,
        amount=float(amount),
        direction="expense",
        category=normalized_category,
    )
    return _store_transactions([transaction])


def create_balance_payments_agent():
    """Create Deep Agent that ingests balance of payments Excel files."""
    instructions = f"{balance_of_payments_agent_prompt}\n\n"

    agent = create_agent(
        model=OPENAI_MODEL,
        tools=[add_expense_transaction, add_income_transaction],
        system_prompt=instructions,
    )
    return agent


async def process_balance_of_payments(file_path: str) -> dict:
    """Run the balance-of-payments ingestion agent for the given uploaded file."""

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Balance workbook not found: {file_path}")

    file_name = path.name
    try:
        parsed_content = await parse_document(str(path))
    except Exception as exc:
        logger.warning("Document parser failed for {}: {}", file_name, exc)

    logger.info("Starting balance of payments agent for {}", file_name)
    agent = create_balance_payments_agent()
    initial_prompt = (
        "You are about to process a balance of payments document. "
        "Leverage the extracted ledger content below when available and use your tools to "
        "persist the normalized transactions so that daily balances stay accurate."
    )

    if parsed_content:
        initial_prompt += (
            "\n\n---\nParsed document content:\n\n" f"{parsed_content}\n\n---\n"
        )

    logger.info("Launching balance of payments agent for {}", file_name)

    summary = await generate_answer(prompt=initial_prompt, agent=agent)

    logger.info("Balance of payments agent finished for {}", file_name)
    return {
        "status": "success",
        "message": summary,
        "file": file_name,
    }
