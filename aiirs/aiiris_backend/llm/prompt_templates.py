from agents import Agent, Runner
from agents.mcp.server import MCPServerStdio
import asyncio
from typing import List


def create_agentic_prompt(
    context: str, query: str, instruction: str = None, mcp_servers: List = None
) -> Agent:

    agent_instructions = f"""Context:
{context}

Soru: {query}{f"\n\nÖzel Talimat: {instruction}" if instruction else ""}

Yukarıdaki bağlam bilgisine dayanarak, soruyu yanıtla. Eğer cevap bağlamda yoksa, 
bilmediğini söyle ve tahmin etme. Eğer cevap local içerik içerisinde yoksa ama web bilgisi içerisinde
varsa dahili belgelerde cevabın bulunamadığını ancak web araması yapılırken bulunduğunu verdiğin cevapta belirt.
Cevap verirken kullandığın bilginin metadatalarını 
aşağıdaki formatta final cevabın sonuna ekle:

Kullanılan Bilgi Metadataları:
- Kaynak: [Source]
- Tarih: [Date]
- Kategori: [Category]"""

    # MCP entegrasyonu ile ajanı oluştur
    agent = Agent(
        name="RAG_Assistant",
        instructions=agent_instructions,
        model="gpt-4.1",
        mcp_servers=mcp_servers or [],  # Yapılandırmada tanımlı MCP sunucularını kullan
    )

    return agent
