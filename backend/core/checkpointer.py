import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from backend.shared.constants import CHECKPOINTER_DB_PATH_STR
from backend.shared.logger import get_logger
from typing import Optional

logger = get_logger("CHECKPOINTER")

# Global checkpointer instance and shared connection
_checkpointer: Optional[AsyncSqliteSaver] = None
_db_connection: Optional[aiosqlite.Connection] = None


async def setup_checkpointer() -> bool:
    """
    Initialize the global checkpointer instance with a single shared database connection.
    Should be called once during application startup.

    Returns:
        bool: True if setup was successful, False otherwise.
    """
    global _checkpointer, _db_connection

    try:
        logger.info("Initializing AsyncSqlite checkpointer with shared connection...")

        # Create a single shared database connection
        _db_connection = await aiosqlite.connect(CHECKPOINTER_DB_PATH_STR)

        # Apply is_alive workaround for the shared connection
        # The buggy version of AsyncSqliteSaver checks for .is_alive()
        if not hasattr(_db_connection, "is_alive"):
            _db_connection.is_alive = lambda: True

        # Create AsyncSqliteSaver using the shared connection
        _checkpointer = AsyncSqliteSaver(_db_connection)

        # Setup database schema (idempotent - safe to call multiple times)
        try:
            await _checkpointer.setup()
        except Exception as e:
            logger.warning(
                f"Checkpointer setup warning (may already be initialized): {e}"
            )

        logger.info(
            f"AsyncSqlite checkpointer initialized at: {CHECKPOINTER_DB_PATH_STR} with shared connection"
        )

        return True
    except Exception as e:
        logger.error(f"Failed to setup checkpointer: {e}")
        logger.warning("Agents will run without persistent checkpointing")
        _checkpointer = None
        if _db_connection:
            await _db_connection.close()
            _db_connection = None
        return False


async def close_checkpointer():
    """
    Close the global checkpointer and shared database connection.
    Should be called during application shutdown.
    """
    global _checkpointer, _db_connection

    try:
        logger.info("Closing AsyncSqlite checkpointer connection...")

        # Close the checkpointer if it exists
        if _checkpointer is not None:
            # AsyncSqliteSaver might have cleanup, but we manage the connection
            _checkpointer = None

        # Close the shared database connection
        if _db_connection is not None:
            await _db_connection.close()
            _db_connection = None

        logger.info("Checkpointer connection closed")
    except Exception as e:
        logger.error(f"Error closing checkpointer: {e}")


def get_checkpointer():
    """
    Get the global checkpointer instance.

    Returns:
        AsyncSqliteSaver: The global checkpointer instance, or None if not initialized
    """
    return _checkpointer
