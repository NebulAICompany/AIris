from agents import Agent
from typing import List
#from aiiris_backend.agent_mcps.web_search_agent import web_search_agent
from agents.tool import WebSearchTool


def create_rag_agent(
    local_context: str,
    web_search_enabled: bool,
    query: str,
    instruction: str = None,
    mcp_servers: List = None,
) -> Agent:

    instruction_part = f"\n\nÖzel Talimat: {instruction}" if instruction else ""
    
    # Web context'i dahil et
    web_context_part = f"Elindeki WebSearchTool'unu kullanarak internette konuyla iligili araştırma yap ve " if web_search_enabled else ""

    agent_instructions = f"""Local Context:
{local_context}

Soru: {query}{instruction_part}


{web_context_part} elindeki bilgilerle soruyu yanıtla. Eğer cevap bağlamda yoksa, 
bilmediğini söyle ve tahmin etme.
Cevap verirken kullandığın bilginin metadatalarını 
aşağıdaki formatta final cevabın sonuna ekle:

Kullanılan Bilgi Metadataları:
- Kaynak: [Source]
- Tarih: [Date]
- Kategori: [Category]"""    # Web search'ün etkin olup olmadığına göre araçları belirle
    tools = []
    if web_search_enabled:
        tools.append(WebSearchTool())
        # web_agent = web_search_agent()
        # tools.append(web_agent.as_tool(
        #     name="WebSearch",
        #     description="Web üzerinde arama yapar ve ilgili sonuçları getirir.",
        #     input_schema={
        #         "type": "object",
        #         "properties": {
        #             "query": {
        #                 "type": "string",
        #                 "description": "Aranacak sorgu metni."
        #             }
        #         },
        #         "required": ["query"]
        #     }
        # ))

    # MCP entegrasyonu ile ajanı oluştur
    agent = Agent(
        name="RAG_Assistant",
        instructions=agent_instructions,
        model="gpt-4o", #4.1 olması gerekiyorsa çevrilsin.
        tools=tools,
    )

    return agent
