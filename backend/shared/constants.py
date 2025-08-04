import os
from dotenv import load_dotenv
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from tavily import TavilyClient
import cohere
from openai import OpenAI
from azure.ai.formrecognizer import DocumentAnalysisClient
from pathlib import Path

load_dotenv()

# Constants for API keys and endpoints
AZURE_LANGUAGE_KEY = os.environ.get('AZURE_LANGUAGE_KEY')
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY')
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
AZURE_LANGUAGE_ENDPOINT = os.environ.get('AZURE_LANGUAGE_ENDPOINT')
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
WOLFRAM_APP_ID = os.getenv("WOLFRAM_APP_ID")


# Constants for API clients
document_analysis_client = DocumentAnalysisClient(
        endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DOCUMENT_INTELLIGENCE_KEY))
openai_client = OpenAI(api_key=OPENAI_API_KEY)
tavily_client = TavilyClient(TAVILY_API_KEY)
ta_credential = AzureKeyCredential(AZURE_LANGUAGE_KEY)
text_analytics_client = TextAnalyticsClient(
        endpoint=AZURE_LANGUAGE_ENDPOINT,
        credential=ta_credential)
co = cohere.ClientV2(api_key=COHERE_API_KEY)

# Constants for file paths

BASE_DIR = Path(__file__).parent.parent  # backend/ directory
PROJECT_ROOT = BASE_DIR.parent  # AIris/ directory

# Database paths
DATABASE_DIR = BASE_DIR / "database"
CHAT_HISTORY_DB_PATH = DATABASE_DIR / "chat_history.db"
MASKED_MAP_JSON_PATH = DATABASE_DIR / "masked_map.json"

# Upload and document paths
UPLOADS_PATH = DATABASE_DIR / "uploads"
CREATED_DOCUMENTS_PATH = DATABASE_DIR / "created_documents"
IMAGES_PATH = UPLOADS_PATH / "images"

# Vectorstore paths
VECTORSTORE_PATH = BASE_DIR / "vectorstore"
FAISS_INDEX_PATH = VECTORSTORE_PATH / "index.faiss"
FAISS_PKL_PATH = VECTORSTORE_PATH / "index.pkl"
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

# Java/Zemberek paths
ZEMBEREK_JAR_PATH = BASE_DIR / "shared" / "zemberek-full.jar"

# File extensions
ALLOWED_FILE_EXTENSIONS = {
    ".pdf", ".txt", ".docx", ".xlsx", ".xls", ".doc",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"
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
ZEMBEREK_JAR_PATH_STR = str(ZEMBEREK_JAR_PATH)
LOGS_DIR_STR = str(LOGS_DIR)
BACKEND_LOG_PATH_STR = str(BACKEND_LOG_PATH)
BACKEND_ERROR_LOG_PATH_STR = str(BACKEND_ERROR_LOG_PATH)