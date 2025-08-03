import os
from dotenv import load_dotenv
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from tavily import TavilyClient
import cohere
from openai import OpenAI
from azure.ai.formrecognizer import DocumentAnalysisClient

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
# TODO: