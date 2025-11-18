from datetime import date
from pathlib import Path
from typing import List, Optional
from backend.core.agents import create_balance_payments_agent
from agents import function_tool
from backend.core.runner import generate_answer
from backend.pipeline.upload import parse_document
from backend.shared.logger import get_logger
from backend.utils.balance_payments_database import (
    BalanceTransaction,
    balance_payments_db,
)
logger = get_logger("BALANCE_TOOLS")


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
def add_income_transaction(amount: float) -> str:
    """Add an income transaction using today's date."""

    if amount is None or amount <= 0:
        return "Amount must be a positive number."

    transaction = BalanceTransaction(
        transaction_date=date.today().isoformat(),
        amount=float(amount),
        direction="income",
    )
    return _store_transactions([transaction])


@function_tool
def add_expense_transaction(amount: float) -> str:
    """Add an expense transaction using today's date."""

    if amount is None or amount <= 0:
        return "Amount must be a positive number."

    transaction = BalanceTransaction(
        transaction_date=date.today().isoformat(),
        amount=float(amount),
        direction="expense",
    )
    return _store_transactions([transaction])


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

