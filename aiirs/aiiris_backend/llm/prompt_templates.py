from agents import Agent
from typing import List

# from aiiris_backend.agent_mcps.web_search_agent import web_search_agent
from agents.tool import WebSearchTool

# Import our custom wolfram function tool
from aiiris_backend.agents.wolfram_alpha_tool import wolfram_alpha_query


def create_rag_agent(
    local_context: str,
    web_search_enabled: bool,
    query: str,
    instruction: str = None,
    mcp_servers: List = None,
    wolfram_enabled: bool = False,
) -> Agent:

    instruction_part = f"\n\nÖzel Talimat: {instruction}" if instruction else ""

    # Web context'i dahil et
    web_context_part = (
        f"Elindeki WebSearchTool'unu kullanarak internette konuyla ilgili araştırma yap ve "
        if web_search_enabled
        else ""
    )

    # Wolfram context'i dahil et
    wolfram_context_part = (
        f"Elindeki wolfram_alpha_query fonksiyonunu kullanarak matematiksel hesaplamalar, bilimsel veriler veya istatistiksel analizler yap ve "
        if wolfram_enabled
        else ""
    )

    tools = []
    if web_search_enabled:
        tools.append(WebSearchTool())

    if wolfram_enabled:
        tools.append(wolfram_alpha_query)

    # Update instructions to include Wolfram Alpha capabilities
    wolfram_instructions = (
        """
Eğer soru aşağıdaki konulardan birini içeriyorsa, wolfram_alpha_query aracını kullan:
- Matematiksel hesaplamalar (denklemler, türevler, integraller, vb.)
- Bilimsel hesaplamalar ve veriler
- İstatistiksel analizler
- Birim dönüşümleri
- Güncel veriler (nüfus, ekonomik göstergeler, vb.)
- Fizik, kimya veya mühendislik hesaplamaları
"""
        if wolfram_enabled
        else ""
    )

    agent_instructions = f"""Local Context:
{local_context}

Soru: {query}{instruction_part}

{wolfram_instructions}
{wolfram_context_part}{web_context_part}elindeki bilgilerle soruyu yanıtla. Eğer cevap bağlamda yoksa, 
bilmediğini söyle ve tahmin etme.
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
        model="gpt-4.1",  # 4.1 olması gerekiyorsa çevrilsin.
        tools=tools,
    )

    return agent
