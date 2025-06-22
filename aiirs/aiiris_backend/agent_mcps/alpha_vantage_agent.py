import asyncio
import os
from typing import Optional, Dict, Any
from agents import Agent, Runner, function_tool
from agents.mcp import MCPServerStdio
from pathlib import Path
import requests
import json
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
import dotenv

# Try to load .env file safely
env_path = PROJECT_ROOT / ".env"
try:
    if env_path.exists():
        dotenv.load_dotenv(env_path)
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

# Validate API key availability
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
if not ALPHA_VANTAGE_API_KEY:
    print("Warning: ALPHA_VANTAGE_API_KEY not found in environment variables")


@function_tool
async def get_stock_quote(symbol: str) -> str:
    """
    Get real-time stock quote for a given symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')

    Returns:
        Current stock price and basic information
    """
    try:
        if not ALPHA_VANTAGE_API_KEY:
            return "❌ Alpha Vantage API key not configured. Please set ALPHA_VANTAGE_API_KEY environment variable."

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper(),
            "apikey": ALPHA_VANTAGE_API_KEY,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "Global Quote" in data:
            quote = data["Global Quote"]
            result = f"""
📈 **{symbol.upper()} Hisse Senedi Bilgileri:**
• **Fiyat:** ${quote.get('05. price', 'N/A')}
• **Değişim:** {quote.get('09. change', 'N/A')} ({quote.get('10. change percent', 'N/A')})
• **Açılış:** ${quote.get('02. open', 'N/A')}
• **Yüksek:** ${quote.get('03. high', 'N/A')}
• **Düşük:** ${quote.get('04. low', 'N/A')}
• **Önceki Kapanış:** ${quote.get('08. previous close', 'N/A')}
• **Son Güncelleme:** {quote.get('07. latest trading day', 'N/A')}
            """
            return result.strip()
        else:
            return f"❌ {symbol.upper()} için hisse senedi bilgisi bulunamadı. Lütfen geçerli bir hisse senedi sembolü girin."

    except Exception as e:
        return f"❌ Hisse senedi verisi alınırken hata oluştu: {str(e)}"


@function_tool
async def get_company_overview(symbol: str) -> str:
    """
    Get detailed company information and fundamentals.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')

    Returns:
        Company overview including sector, market cap, P/E ratio, etc.
    """
    try:
        if not ALPHA_VANTAGE_API_KEY:
            return "❌ Alpha Vantage API key not configured."

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": ALPHA_VANTAGE_API_KEY,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data and "Symbol" in data:
            result = f"""
🏢 **{data.get('Name', 'N/A')} ({symbol.upper()}) Şirket Genel Bakış:**

📊 **Temel Bilgiler:**
• **Sektör:** {data.get('Sector', 'N/A')}
• **Endüstri:** {data.get('Industry', 'N/A')}
• **Piyasa Değeri:** ${data.get('MarketCapitalization', 'N/A')}
• **P/E Oranı:** {data.get('PERatio', 'N/A')}
• **Temettü Verimi:** {data.get('DividendYield', 'N/A')}

💰 **Finansal Metrikler:**
• **EPS:** ${data.get('EPS', 'N/A')}
• **Beta:** {data.get('Beta', 'N/A')}
• **52 Hafta Yüksek:** ${data.get('52WeekHigh', 'N/A')}
• **52 Hafta Düşük:** ${data.get('52WeekLow', 'N/A')}

📝 **Açıklama:**
{data.get('Description', 'Açıklama mevcut değil.')[:300]}...
            """
            return result.strip()
        else:
            return f"❌ {symbol.upper()} için şirket bilgisi bulunamadı."

    except Exception as e:
        return f"❌ Şirket bilgisi alınırken hata oluştu: {str(e)}"


@function_tool
async def get_crypto_rate(from_currency: str, to_currency: str = "USD") -> str:
    """
    Get cryptocurrency exchange rate.

    Args:
        from_currency: Crypto symbol (e.g., 'BTC', 'ETH', 'ADA')
        to_currency: Target currency (default: 'USD')

    Returns:
        Current cryptocurrency exchange rate
    """
    try:
        if not ALPHA_VANTAGE_API_KEY:
            return "❌ Alpha Vantage API key not configured."

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "apikey": ALPHA_VANTAGE_API_KEY,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "Realtime Currency Exchange Rate" in data:
            rate_data = data["Realtime Currency Exchange Rate"]
            result = f"""
₿ **{from_currency.upper()}/{to_currency.upper()} Kripto Para Kuru:**
• **Döviz Kuru:** {rate_data.get('5. Exchange Rate', 'N/A')}
• **Son Güncelleme:** {rate_data.get('6. Last Refreshed', 'N/A')}
• **Zaman Dilimi:** {rate_data.get('7. Time Zone', 'N/A')}
            """
            return result.strip()
        else:
            return f"❌ {from_currency.upper()}/{to_currency.upper()} için kripto para kuru bulunamadı."

    except Exception as e:
        return f"❌ Kripto para kuru alınırken hata oluştu: {str(e)}"


async def create_alpha_vantage_agent_with_mcp():
    """Create Alpha Vantage agent with MCP server connection"""
    try:
        current_env = os.environ.copy()
        current_env["ALPHA_VANTAGE_API_KEY"] = ALPHA_VANTAGE_API_KEY

        mcp_server = MCPServerStdio(
            params={
                "command": "python",
                "args": ["-m", "src.alpha_vantage_mcp.server"],
                "cwd": str(PROJECT_ROOT / "alpha-vantage-mcp"),
                "env": current_env,
            }
        )

        agent = Agent(
            name="Alpha Vantage Finance Agent",
            instructions="""Sen gelişmiş bir finansal veri analisti asistanısın. 
            
            Elindeki Alpha Vantage araçlarını kullanarak:
            - Hisse senedi fiyatları ve kotasyonları
            - Şirket bilgileri (sektör, endüstri, piyasa değeri)
            - Kripto para kurları
            - Tarihsel fiyat serileri
            - Opsiyon zinciri verileri
            
            sağlayabilirsin. Tüm finansal sorguları doğru araçları kullanarak yanıtla.
            
            YANIT PROTOKOLÜ:
            1. Kullanıcının finansal sorusunu analiz et
            2. En uygun Alpha Vantage aracını seç
            3. Veriyi getir ve analiz et
            4. Anlaşılır ve actionable insights sun
            5. Kaynak metadatalarını belirt
            
            ⚠️ **UYARILAR:**
            - Yatırım tavsiyesi verme, sadece veri analizi yap
            - API limitlerini göz önünde bulundur
            - Hata durumunda kullanıcıyı bilgilendir""",
            mcp_servers=[mcp_server],
        )

        return agent, mcp_server

    except Exception as e:
        print(f"Alpha Vantage MCP bağlantı hatası: {str(e)}")
        return None, None


alpha_vantage_agent = Agent(
    name="alpha_vantage_agent",
    instructions="""Sen uzman bir finansal veri analistisisin.
    
    YETENEKLERE SAHIP OLDUĞUN ALANLAR:
    🏦 **Hisse Senedi Analizi:**
    - Gerçek zamanlı hisse fiyatları (get_stock_quote kullan)
    - Şirket temel bilgileri (get_company_overview kullan)
    - Tarihsel fiyat performansı
    
    💰 **Kripto Para Verileri:**
    - Anlık kripto kurları (get_crypto_rate kullan)
    - Günlük/haftalık/aylık zaman serileri
    - Kripto piyasa analizi
    
    📊 **Teknik Analiz:**
    - Temel finansal metrikler
    - Piyasa değerlendirmeleri
    - Risk analizi
    
    YANIT PROTOKOLÜ:
    1. Kullanıcının finansal sorusunu analiz et
    2. Uygun aracı kullanarak veriyi getir
    3. Anlaşılır ve actionable insights sun
    4. Kaynak metadatalarını belirt
    
    ⚠️ **UYARILAR:**
    - Yatırım tavsiyesi verme, sadece veri analizi yap
    - API limitlerini göz önünde bulundur
    - Hata durumunda kullanıcıyı bilgilendir
    
    🔧 **ARAÇLARIN:**
    - get_stock_quote: Hisse senedi fiyatları için
    - get_company_overview: Şirket detayları için  
    - get_crypto_rate: Kripto para kurları için
    
    Her sorgu için en uygun aracı seç ve kullan.""",
    tools=[get_stock_quote, get_company_overview, get_crypto_rate],
)
