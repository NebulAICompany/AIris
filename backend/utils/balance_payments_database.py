import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from collections import Counter
from backend.shared.constants import (
    BALANCE_PAYMENTS_DB_PATH,
    BALANCE_TRANSACTION_CATEGORIES,
)
from backend.shared.logger import get_logger
logger = get_logger("BALANCE_DB")

CATEGORY_SQL_VALUES = "', '".join(BALANCE_TRANSACTION_CATEGORIES)
CATEGORY_CHECK_CLAUSE = f"('{CATEGORY_SQL_VALUES}')"

@dataclass
class BalanceTransaction:
    transaction_date: str
    amount: float
    direction: str
    category: Optional[str] = None


class BalancePaymentsDatabase:
    """SQLite-backed storage for balance of payments transactions and daily summaries."""

    def __init__(self, db_path: Path = BALANCE_PAYMENTS_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS bop_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transaction_date TEXT NOT NULL,
                        amount REAL NOT NULL,
                        direction TEXT NOT NULL CHECK(direction IN ('income', 'expense')),
                        category TEXT CHECK(category IN {CATEGORY_CHECK_CLAUSE} OR category IS NULL),
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                self._ensure_category_column(conn)
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_bop_transactions_date
                        ON bop_transactions(transaction_date)
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS bop_daily_balances (
                        calendar_date TEXT PRIMARY KEY,
                        total_income REAL NOT NULL,
                        total_expense REAL NOT NULL,
                        net REAL NOT NULL,
                        last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
                logger.info(
                    "Balance of payments database initialized at {}",
                    self.db_path,
                )
        except Exception as exc:
            logger.error(
                "Failed to initialize balance of payments database: {}",
                exc,
            )
            raise

    def _ensure_category_column(self, conn: sqlite3.Connection) -> None:
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(bop_transactions)")
        }
        if "category" not in columns:
            conn.execute(
                f"""
                ALTER TABLE bop_transactions
                ADD COLUMN category TEXT CHECK(category IN {CATEGORY_CHECK_CLAUSE} OR category IS NULL)
                """
            )

    def store_transactions(
        self,
        transactions: Sequence[BalanceTransaction],
    ) -> int:
        if not transactions:
            logger.warning("No transactions provided to store; skipping")
            return 0

        try:
            with self._connect() as conn:
                dates_to_update: List[str] = []

                insert_rows: List[tuple[str, float, str, Optional[str]]] = []
                direction_counts: Counter[str] = Counter()
                category_counts: Counter[str] = Counter()
                for tx in transactions:
                    try:
                        normalized_date = datetime.fromisoformat(
                            tx.transaction_date
                        ).date().isoformat()
                    except ValueError as exc:
                        raise ValueError(
                            f"Transaction date must be ISO formatted YYYY-MM-DD, got '{tx.transaction_date}'."
                        ) from exc

                    category: Optional[str] = None
                    if tx.category is not None:
                        category = tx.category.strip()
                        if not category:
                            category = None
                    if category is not None and category not in BALANCE_TRANSACTION_CATEGORIES:
                        raise ValueError(
                            "Invalid category. Expected one of: "
                            + ", ".join(BALANCE_TRANSACTION_CATEGORIES)
                        )

                    insert_rows.append(
                        (
                            normalized_date,
                            float(tx.amount),
                            tx.direction,
                            category,
                        )
                    )
                    direction_counts[tx.direction] += 1
                    category_key = category or "(none)"
                    category_counts[category_key] += 1

                conn.executemany(
                    """
                    INSERT INTO bop_transactions (
                        transaction_date,
                        amount,
                        direction,
                        category
                    ) VALUES (?, ?, ?, ?)
                    """,
                    insert_rows,
                )

                dates_to_update.extend(tx.transaction_date for tx in transactions)
                self._recalculate_daily_balances(conn, set(dates_to_update))
                conn.commit()
                return True
        except Exception as exc:
            logger.error("Failed to store balance transactions: {}", exc)
            raise

    def _recalculate_daily_balances(
        self, conn: sqlite3.Connection, dates: Iterable[str]
    ) -> None:
        unique_dates = sorted(set(dates))
        for calendar_date in unique_dates:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN direction = 'income' THEN amount END), 0.0) AS income,
                    COALESCE(SUM(CASE WHEN direction = 'expense' THEN amount END), 0.0) AS expense
                FROM bop_transactions
                WHERE transaction_date = ?
                """,
                (calendar_date,),
            ).fetchone()

            income = float(row["income"] or 0.0)
            expense = float(row["expense"] or 0.0)

            if income == 0.0 and expense == 0.0:
                conn.execute(
                    "DELETE FROM bop_daily_balances WHERE calendar_date = ?",
                    (calendar_date,),
                )
                continue

            net = income - expense
            conn.execute(
                """
                INSERT INTO bop_daily_balances (calendar_date, total_income, total_expense, net, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(calendar_date) DO UPDATE SET
                    total_income = excluded.total_income,
                    total_expense = excluded.total_expense,
                    net = excluded.net,
                    last_updated = CURRENT_TIMESTAMP
                """,
                (calendar_date, income, expense, net),
            )

    def get_daily_balances(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, float]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT calendar_date, total_income, total_expense, net
                FROM bop_daily_balances
                WHERE calendar_date BETWEEN ? AND ?
                ORDER BY calendar_date ASC
                """,
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

        results: List[Dict[str, float]] = []
        running_net = 0.0

        for row in rows:
            income = float(row["total_income"])
            expense = float(row["total_expense"])
            daily_net = income - expense
            running_net += daily_net

            results.append(
                {
                    "date": row["calendar_date"],
                    "income": income,
                    "expense": expense,
                    "net": running_net,
                }
            )

        return results

    def get_transactions_for_date(
        self, target_date: date
    ) -> List[Dict[str, Optional[str]]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT transaction_date, amount, direction, category
                FROM bop_transactions
                WHERE transaction_date = ?
                ORDER BY created_at ASC
                """,
                (target_date.isoformat(),),
            ).fetchall()

        results: List[Dict[str, Optional[str]]] = []
        for row in rows:
            results.append(
                {
                    "date": row["transaction_date"],
                    "amount": float(row["amount"]),
                    "direction": row["direction"],
                    "category": row["category"],
                }
            )
        return results

    def latest_activity_date(self) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT MAX(transaction_date) AS latest_date
                FROM bop_transactions
                """
            ).fetchone()
        return row["latest_date"] if row and row["latest_date"] else None


balance_payments_db = BalancePaymentsDatabase()
