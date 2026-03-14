import os
from typing import List, Optional
from dotenv import load_dotenv
from azure.ai.textanalytics.aio import TextAnalyticsClient as AsyncTextAnalyticsClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from tavily import TavilyClient
import cohere
from openai import OpenAI, AsyncOpenAI
from pathlib import Path
from concurrent_openai import ConcurrentOpenAI
from langchain_core.tracers.stdout import ConsoleCallbackHandler
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_qwq import ChatQwen

load_dotenv()

AZURE_LANGUAGE_KEY = os.environ.get("AZURE_LANGUAGE_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
AZURE_LANGUAGE_ENDPOINT = os.environ.get("AZURE_LANGUAGE_ENDPOINT")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY")
MARKETSTACK_BASE_URL = os.getenv(
    "MARKETSTACK_BASE_URL",
    f"http://api.marketstack.com/v2/",
)
MARKETSTACK_EOD_URL = MARKETSTACK_BASE_URL + "eod"
MARKETSTACK_COMPANY_INFO_URL = MARKETSTACK_BASE_URL + "tickerinfo"
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
WOLFRAM_APP_ID = os.getenv("WOLFRAM_APP_ID")
MARKETSTACK_BASE_URL = "https://api.marketstack.com/v2"

# Constants for API clients

document_intelligence_client = DocumentIntelligenceClient(
    endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    credential=AzureKeyCredential(str(AZURE_DOCUMENT_INTELLIGENCE_KEY)),
)

async_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
concurrent_client = ConcurrentOpenAI(
    client=async_openai_client,
    max_concurrent_requests=5,
    requests_per_minute=450,  # hesabınızdaki RPM’e göre ayarlayın
    tokens_per_minute=27000,
)
tavily_client = TavilyClient(TAVILY_API_KEY)
ta_credential = AzureKeyCredential(AZURE_LANGUAGE_KEY)
text_analytics_client = TextAnalyticsClient(
    endpoint=AZURE_LANGUAGE_ENDPOINT, credential=ta_credential
)

async_text_analytics_client = AsyncTextAnalyticsClient(
    endpoint=AZURE_LANGUAGE_ENDPOINT, credential=ta_credential
)
co = cohere.ClientV2(api_key=COHERE_API_KEY)

# Constants for file paths

BASE_DIR = Path(__file__).parent.parent  # backend/ directory
PROJECT_ROOT = BASE_DIR.parent  # AIris/ directory

# Database paths
DATABASE_DIR = BASE_DIR / "database"
CHAT_HISTORY_DB_PATH = DATABASE_DIR / "chat_history.db"
MASKED_MAP_JSON_PATH = DATABASE_DIR / "masked_map.json"

# Charts directory - Use absolute path to prevent backend/backend issue
CHARTS_DIR = PROJECT_ROOT / "backend" / "database" / "charts"
CHART_DATA_FILE = CHARTS_DIR / "chart_data.json"

# Market data database path
MARKET_DATA_DB_PATH = DATABASE_DIR / "market_data.db"

# Uploads tracking database path
UPLOADS_DB_PATH = DATABASE_DIR / "uploads_tracking.db"

# Balance of payments database path
BALANCE_PAYMENTS_DB_PATH = DATABASE_DIR / "balance_payments.db"

# Checkpointer database path (SQLite)
CHECKPOINTER_DB_PATH = DATABASE_DIR / "checkpoints.db"

# Balance of payments transaction categories
BALANCE_TRANSACTION_CATEGORIES = (
    "İşletme Faaliyetleri",
    "Yatırım Faaliyetleri",
    "Finansman Faaliyetleri",
)

BALANCE_TRANSACTION_CATEGORY_ALIASES = {
    "operating activities": "İşletme Faaliyetleri",
    "operating activity": "İşletme Faaliyetleri",
    "işletme faaliyetleri": "İşletme Faaliyetleri",
    "investment activities": "Yatırım Faaliyetleri",
    "investment activity": "Yatırım Faaliyetleri",
    "yatırım faaliyetleri": "Yatırım Faaliyetleri",
    "financing activities": "Finansman Faaliyetleri",
    "financing activity": "Finansman Faaliyetleri",
    "finansman faaliyetleri": "Finansman Faaliyetleri",
}

# Upload and document paths
UPLOADS_PATH = DATABASE_DIR / "uploads"
CREATED_DOCUMENTS_PATH = DATABASE_DIR / "created_documents"
IMAGES_PATH = UPLOADS_PATH / "images"

# Vectorstore paths
VECTORSTORE_PATH = DATABASE_DIR / "vectorstore"
PII_CHUNK_MAPS_PATH = VECTORSTORE_PATH / "pii_chunk_maps.json"

# Frontend paths
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_SRC_DIR = FRONTEND_DIR / "src"
FRONTEND_RENDERER_DIR = FRONTEND_SRC_DIR / "renderer"
FRONTEND_ASSETS_DIR = FRONTEND_DIR / "assets"

# Logging paths
LOGS_DIR = PROJECT_ROOT / "logs"
BACKEND_LOG_PATH = LOGS_DIR / "backend.log"
BACKEND_ERROR_LOG_PATH = LOGS_DIR / "backend_errors.log"

# File extensions
ALLOWED_FILE_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".docx",
    ".xlsx",
    ".xls",
    ".doc",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
}

# Image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}

# Document extensions
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".docx", ".xlsx", ".xls", ".doc"}

# Convert Path objects to strings for backward compatibility
UPLOADS_PATH_STR = str(UPLOADS_PATH)
CREATED_DOCUMENTS_PATH_STR = str(CREATED_DOCUMENTS_PATH)
IMAGES_PATH_STR = str(IMAGES_PATH)
VECTORSTORE_PATH_STR = str(VECTORSTORE_PATH)
DATABASE_DIR_STR = str(DATABASE_DIR)
CHAT_HISTORY_DB_PATH_STR = str(CHAT_HISTORY_DB_PATH)
MASKED_MAP_JSON_PATH_STR = str(MASKED_MAP_JSON_PATH)
LOGS_DIR_STR = str(LOGS_DIR)
BACKEND_LOG_PATH_STR = str(BACKEND_LOG_PATH)
BACKEND_ERROR_LOG_PATH_STR = str(BACKEND_ERROR_LOG_PATH)
BALANCE_PAYMENTS_DB_PATH_STR = str(BALANCE_PAYMENTS_DB_PATH)
CHECKPOINTER_DB_PATH_STR = str(CHECKPOINTER_DB_PATH)


ANTHROPIC_MODEL = ChatAnthropic(
    model_name="claude-sonnet-4-5-20250929",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_retries=5,
    temperature=0.0,
    max_tokens=64000,
    timeout=120,
    callbacks=[ConsoleCallbackHandler()],
)

OPENAI_MODEL = ChatOpenAI(
    model="gpt-5.2",
    temperature=0.0,
    api_key=os.getenv("OPENAI_API_KEY"),
    frequency_penalty=0.7,
    presence_penalty=0.4,
    max_retries=3,
    callbacks=[ConsoleCallbackHandler()],
)

QWEN_MODEL = ChatQwen(
    model_name="qwen3-max",                  # from your Qwen key
    api_key=os.getenv("QWEN_API_KEY"),
    temperature=0.0,
    max_tokens=8000,                        # adjust for your use case
    timeout=120,
    callbacks=[ConsoleCallbackHandler()],
)

DEEPSEEK_MODEL = ChatOpenAI(
    model="deepseek-chat",                 # or "deepseek-reasoner" if you want the reasoning model
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",   # OpenAI-compatible DeepSeek endpoint
    temperature=0.0,
    max_tokens=8000,                       # adjust as you like
    max_retries=3,
    callbacks=[ConsoleCallbackHandler()],
)

GPT5 = ChatOpenAI(
    model="gpt-5",
    temperature=0.0,
    callbacks=[ConsoleCallbackHandler()],
)

GPT5_MINI = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0.0,
    callbacks=[ConsoleCallbackHandler()],
)

RESEARCH_LLM_REASONING = GPT5
RESEARCH_LLM_FAST = GPT5_MINI

CURRENT_MODEL = OPENAI_MODEL

MARKETSTACK_TICKERS = [
    "AEFES.IS",
    "AKBNK.IS",
    "ASELS.IS",
    "ASTOR.IS",
    "BIMAS.IS",
    "CIMSA.IS",
    "EKGYO.IS",
    "ENKAI.IS",
    "EREGL.IS",
    "FROTO.IS",
    "GARAN.IS",
    "GUBRF.IS",
    "ISCTR.IS",
    "KCHOL.IS",
    "KOZAL.IS",
    "KRDMD.IS",
    "MGROS.IS",
    "PETKM.IS",
    "PGSUS.IS",
    "SAHOL.IS",
    "SASA.IS",
    "SISE.IS",
    "TAVHL.IS",
    "TCELL.IS",
    "THYAO.IS",
    "TOASO.IS",
    "TTKOM.IS",
    "TUPRS.IS",
    "ULKER.IS",
    "YKBNK.IS",
]

# Global variable for selected files in RAG queries
SELECTED_FILES: Optional[List[str]] = None

# Global variable for original user query
ORIGINAL_USER_QUERY: Optional[str] = None


def set_selected_files(files: Optional[List[str]]) -> None:
    """Set the global selected files for RAG queries."""
    global SELECTED_FILES
    SELECTED_FILES = files


def get_selected_files() -> Optional[List[str]]:
    """Get the global selected files for RAG queries."""
    return SELECTED_FILES


def set_original_user_query(query: Optional[str]) -> None:
    """Set the global original user query."""
    global ORIGINAL_USER_QUERY
    ORIGINAL_USER_QUERY = query


def get_original_user_query() -> Optional[str]:
    """Get the global original user query."""
    return ORIGINAL_USER_QUERY


def get_synthesizer_token_limit_for_fast() -> int:
    """Return a safe synthesis batch token budget (capped for SPD-RAG recursion)."""
    max_context_map = {
        "gpt-5": 400_000,
        "gpt-5-mini": 400_000,
    }

    model_name = getattr(RESEARCH_LLM_FAST, "model_name", None) or getattr(
        RESEARCH_LLM_FAST, "model", None
    )
    max_ctx = max_context_map.get(model_name, 128_000)
    return min(750_000, int(max_ctx * 0.75))
