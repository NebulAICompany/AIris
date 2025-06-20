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
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA,
    }
    
    def format(self, record):
        # Add color for console output
        if hasattr(record, 'is_console') and record.is_console:
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
            
        return super().format(record)

class ContextFilter(logging.Filter):
    """Filter to add context tags to log records"""
    
    def __init__(self, context_tag=None):
        super().__init__()
        self.context_tag = context_tag
    
    def filter(self, record):
        if self.context_tag:
            record.context = f"[{self.context_tag}]"
        else:
            record.context = ""
        return True

def setup_logger():
    """Setup centralized logging configuration"""
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create logger
    logger = logging.getLogger('aiiris_backend')
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler with rotation (10MB max, keep 5 files)
    log_file = os.path.join(logs_dir, 'aiiris_backend.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Separate error log file
    error_log_file = os.path.join(logs_dir, 'aiiris_backend_errors.log')
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(context)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(context)s %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Add context filter
    context_filter = ContextFilter("APP")
    
    # Setup handlers
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(context_filter)
    
    error_handler.setFormatter(file_formatter)
    error_handler.addFilter(context_filter)
    
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(context_filter)
    
    # Mark console records for coloring
    def add_console_flag(record):
        record.is_console = True
        return True
    
    console_filter = logging.Filter()
    console_filter.filter = add_console_flag
    console_handler.addFilter(console_filter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(context_tag=None):
    """Get logger instance with optional context tag"""
    
    logger = logging.getLogger('aiiris_backend')
    
    # If logger not configured yet, set it up
    if not logger.handlers:
        setup_logger()
    
    # If context tag provided, create a logger adapter
    if context_tag:
        # Create a child logger with context filter
        context_logger = logger.getChild(context_tag)
        
        # Add context filter to all handlers
        for handler in logger.handlers:
            # Remove any existing context filters
            handler.filters = [f for f in handler.filters if not isinstance(f, ContextFilter)]
            # Add new context filter
            handler.addFilter(ContextFilter(context_tag))
        
        return context_logger
    
    return logger

# Initialize the logger
logger = setup_logger() 