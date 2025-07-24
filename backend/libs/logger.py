import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import colorama
from colorama import Fore, Style

# Initialize colorama for Windows
colorama.init()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    def format(self, record):
        # Ensure context attribute exists
        if not hasattr(record, "context"):
            record.context = ""

        # Add color for console output
        if hasattr(record, "is_console") and record.is_console:
            color = self.COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"

        return super().format(record)


class ContextFilter(logging.Filter):
    """Filter to add context tags to log records"""

    def __init__(self, context_tag=None):
        super().__init__()
        self.context_tag = context_tag

    def filter(self, record):
        # Always set context, even if empty
        record.context = f"[{self.context_tag}]" if self.context_tag else ""
        return True


# Global flag to track if base logger is set up
_base_logger_setup = False


def setup_base_logger():
    """Setup centralized logging configuration - only once"""
    global _base_logger_setup

    if _base_logger_setup:
        return

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Create base logger
    base_logger = logging.getLogger("backend")
    base_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    base_logger.handlers.clear()

    # File handler with rotation (10MB max, keep 5 files)
    log_file = os.path.join(logs_dir, "backend.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
    )
    file_handler.setLevel(logging.DEBUG)

    # Separate error log file
    error_log_file = os.path.join(logs_dir, "backend_errors.log")
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a safe formatter class that handles missing context
    class SafeFormatter(logging.Formatter):
        def format(self, record):
            if not hasattr(record, "context"):
                record.context = ""
            return super().format(record)

    # Formatters
    file_formatter = SafeFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(context)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = ColoredFormatter(
        "%(asctime)s - %(levelname)s - %(context)s %(message)s", datefmt="%H:%M:%S"
    )

    # Setup handlers
    file_handler.setFormatter(file_formatter)
    error_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    # Add context filter to base logger
    base_logger.addFilter(ContextFilter())

    # Mark console records for coloring
    def add_console_flag(record):
        record.is_console = True
        return True

    console_filter = logging.Filter()
    console_filter.filter = add_console_flag
    console_handler.addFilter(console_filter)

    # Add handlers to base logger
    base_logger.addHandler(file_handler)
    base_logger.addHandler(error_handler)
    base_logger.addHandler(console_handler)

    _base_logger_setup = True


def get_logger(context_tag=None):
    """Get logger instance with optional context tag"""

    # Ensure base logger is set up
    setup_base_logger()

    if context_tag:
        # Create a child logger with the context tag
        logger_name = f"backend.{context_tag}"
        context_logger = logging.getLogger(logger_name)

        # Only add context filter if not already added
        if not any(isinstance(f, ContextFilter) for f in context_logger.filters):
            context_logger.addFilter(ContextFilter(context_tag))

        return context_logger
    else:
        # Return base logger
        base_logger = logging.getLogger("backend")
        return base_logger


# For backward compatibility
def setup_logger():
    """Deprecated: Use get_logger() instead"""
    setup_base_logger()
    return logging.getLogger("backend")


# Initialize the base logger
setup_base_logger()
