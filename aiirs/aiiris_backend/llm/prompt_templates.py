from agents import Agent
from typing import List
from aiiris_backend.agents.web_search_agent import web_search_agent


def create_rag_agent(
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
        tools=[web_search_agent],  # Yapılandırmada tanımlı MCP sunucularını kullan
    )

    return agent
