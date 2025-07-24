import os
import asyncio
from agents import Agent
from agents.mcp import MCPServerStdio
from pathlib import Path
from agents import Runner

PROJECT_ROOT = Path(__file__).parent.parent
import dotenv

# Try to load .env file safely
env_path = PROJECT_ROOT / ".env"
try:
    if env_path.exists():
        dotenv.load_dotenv(env_path)
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

mcp_server = MCPServerStdio(
    params={
        "command": "python",
        "args": ["-m", "src.alpha_vantage_mcp.server"],
        "cwd": str(PROJECT_ROOT / "backend/alpha-vantage-mcp"),
        "env": os.environ.copy(),
    }
)

alpha_vantage_agent = Agent(
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


async def main():
    await mcp_server.connect()
    result = await Runner.run(alpha_vantage_agent, "Tesla hisse senedi ne kadar  ")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
