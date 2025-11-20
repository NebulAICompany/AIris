from datetime import date, datetime
from pathlib import Path
from typing import List, Optional
from agents import function_tool
from backend.core.runner import generate_answer
from backend.pipeline.upload import parse_document
from backend.shared.logger import get_logger
from backend.utils.balance_payments_database import (
    BalanceTransaction,
    balance_payments_db,
)
from backend.core.prompts import balance_of_payments_agent_prompt
from backend.shared.constants import OPENAI_MODEL
from agents import Agent
logger = get_logger("BALANCE_TOOLS")


def _normalize_transaction_date(raw_date: Optional[str]) -> str:
    """Validate and normalize incoming transaction date strings."""

    if raw_date is None:
        return date.today().isoformat()

    cleaned = raw_date.strip()
    if not cleaned:
        return date.today().isoformat()

    # Accept a few common ledger date formats in addition to ISO.
    candidate_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"]

    for fmt in candidate_formats:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue

    # Finally, try Python's flexible ISO parser.
    try:
        return datetime.fromisoformat(cleaned).date().isoformat()
    except ValueError as exc:
        logger.warning("Received unrecognized transaction date format: %s", cleaned)
        raise ValueError(
            "Invalid transaction_date. Use ISO format YYYY-MM-DD."
        ) from exc


def _store_transactions(transactions: List[BalanceTransaction]) -> str:
    try:
        stored = balance_payments_db.store_transactions(
            transactions=transactions,
        )
        return f"Stored {stored} transaction(s)."
    except Exception as exc:
        logger.error("Failed to store balance transaction: %s", exc)
        return f"Error while storing transaction: {exc}"


@function_tool
def add_income_transaction(amount: float, transaction_date: Optional[str] = None) -> str:
    """Persist an income entry with the provided ISO date (defaults to today)."""

    if amount is None or amount <= 0:
        return "Amount must be a positive number."

    try:
        normalized_date = _normalize_transaction_date(transaction_date)
    except ValueError as exc:
        logger.warning("Income transaction rejected due to invalid date: %s", exc)
        return str(exc)

    logger.info(
        f"Adding income transaction of amount {amount} for {normalized_date}"
    )

    transaction = BalanceTransaction(
        transaction_date=normalized_date,
        amount=float(amount),
        direction="income",
    )
    return _store_transactions([transaction])


@function_tool
def add_expense_transaction(amount: float, transaction_date: Optional[str] = None) -> str:
    """Persist an expense entry with the provided ISO date (defaults to today)."""

    if amount is None or amount <= 0:
        return "Amount must be a positive number."

    try:
        normalized_date = _normalize_transaction_date(transaction_date)
    except ValueError as exc:
        logger.warning("Expense transaction rejected due to invalid date: %s", exc)
        return str(exc)

    logger.info(
        f"Adding expense transaction of amount {amount} for {normalized_date}"
    )

    transaction = BalanceTransaction(
        transaction_date=normalized_date,
        amount=float(amount),
        direction="expense",
    )
    return _store_transactions([transaction])

def create_balance_payments_agent() -> Agent:
    """Create agent that ingests balance of payments Excel files."""
    instructions = (f"{balance_of_payments_agent_prompt}\n\n")

    agent = Agent(
        name="Balance_of_Payments_Agent",
        instructions=instructions,
        model=OPENAI_MODEL,
        tools=[add_expense_transaction, add_income_transaction],
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
        logger.warning("Document parser failed for %s: %s", file_name, exc)

    logger.info("Starting balance of payments agent for %s", file_name)
    agent = create_balance_payments_agent()
    initial_prompt = (
        "You are about to process a balance of payments document. "
        "Leverage the extracted ledger content below when available and use your tools to "
        "persist the normalized transactions so that daily balances stay accurate."
    )

    if parsed_content:
        initial_prompt += (
            "\n\n---\nParsed document content:\n\n"
            f"{parsed_content}\n\n---\n"
        )

    logger.info("Launching balance of payments agent for %s", file_name)

    summary = await generate_answer(prompt=initial_prompt, agent=agent)

    logger.info("Balance of payments agent finished for %s", file_name)
    return {
        "status": "success",
        "message": summary,
        "file": file_name,
    }

