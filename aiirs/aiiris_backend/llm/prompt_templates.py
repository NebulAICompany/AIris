from agents import Agent, Runner, function_tool
from typing import List
from agents.tool import WebSearchTool
from aiiris_backend.agent_mcps.office_agent import office_agent

@function_tool
async def route_to_office_agent(task: str) -> str:
    """
    Routes office-related tasks to the specialized Office Agent.
    Use this for Word, Excel operations.
    
    Args:
        task: Detailed description of the office task to perform
    """
    result = await Runner.run(office_agent, task)
    return result.content if hasattr(result, 'content') else str(result)


def create_rag_agent(
    local_context: str,
    web_search_enabled: bool,
    query: str,
    instruction: str = None,
    mcp_servers: List = None,
) -> Agent:

    instruction_part = f"\n\n🎯 Özel Talimat: {instruction}" if instruction else ""
    
    # Web context'i dahil et
    web_context_part = f"🌐 Web araması etkinleştirildi - WebSearchTool'unu kullanarak güncel bilgilere erişebilirsin." if web_search_enabled else "🔒 Web araması devre dışı - sadece yerel bilgileri kullan."
    
    # Office context'i dahil et
    office_context_part = """
📂 Office İşlemleri:
Office Agent'a yönlendirebileceğin görevler:
• Word belgesi oluşturma, düzenleme ve PDF'ye dönüştürme
• Excel dosyası oluşturma ve veri analizi
• Word belgelerinden tablo çıkarma ve yapılandırma
• Dosya format dönüştürmeleri
• Toplu belge işlemleri
"""

    agent_instructions = f"""🤖 Sen gelişmiş bir RAG (Retrieval-Augmented Generation) Asistanısın. 

📊 **Yerel Bağlam Bilgileri:**
{local_context}

🔍 **Web Arama Durumu:** {web_context_part}

{office_context_part}

❓ **Mevcut Sorgu:**
{query}{instruction_part}

📋 **Görev Tanımın ve Sorumlulukların:**

🎯 **Ana Görevler:**
1. **Bilgi Analizi:** Sorguyu analiz et ve hangi kaynakları kullanman gerektiğini belirle
2. **Akıllı Yönlendirme:** Office işlemleri için route_to_office_agent fonksiyonunu kullan
3. **Kapsamlı Yanıtlama:** Mevcut bilgilerle detaylı ve doğru yanıtlar ver
4. **Kaynak Belgeleme:** Kullandığın bilgilerin metadatalarını sağla

🔧 **İşlem Protokolleri:**

**📝 Sorgu Yanıtlama İçin:**
- Önce yerel bağlamda cevabı ara
- Gerekirse web araması yap (etkinse)
- Bilgi eksikse açıkça belirt, tahmin etme
- Yanıtlarını destekleyici kanıtlarla güçlendir

**🏢 Office İşlemleri İçin:**
Aşağıdaki durumlardan herhangi birinde route_to_office_agent'ı kullan:
- "Word belgesi oluştur/düzenle/dönüştür"
- "Excel dosyası hazırla/analiz et"
- "PDF'ye çevir"
- "Tablo çıkar/düzenle"
- "Dosya formatını değiştir"
- Herhangi bir office uygulaması gerektiren işlem

**🌐 Web Araması İçin:**
- Güncel bilgi gerektiğinde
- Yerel bağlamda bilgi bulunamadığında
- Karşılaştırmalı analiz için
- Trend ve gelişmeleri araştırırken

📐 **Kalite Standartları:**
- ✅ Doğru ve güncel bilgi sağla
- ✅ Kaynaklarını şeffaf bir şekilde belge
- ✅ Belirsizlikleri açıkça ifade et
- ✅ Kullanıcı dostu ve anlaşılır dil kullan
- ✅ Yapılandırılmış ve organize yanıtlar ver

📊 **Yanıt Formatı:**
Her yanıtının sonunda aşağıdaki metadata formatını kullan:

```
🗂️ Kullanılan Bilgi Metadataları:
- 📂 Kaynak: [Source]
- 📅 Tarih: [Date]
- 🏷️ Kategori: [Category]
- 🔧 Kullanılan Araçlar: [Tools Used]
- ⚡ İşlem Durumu: [Success/Partial/Failed]
```

🚨 **Kritik Kurallar:**
- Bilmediğin konularda spekülasyon yapma
- Office işlemlerini kendın yapmaya çalışma, Office Agent'a yönlendir
- Her zaman güvenilir kaynakları tercih et
- Kullanıcının gizliliğini ve veri güvenliğini koru

💡 **Proaktif Yaklaşım:**
- Alternatif çözümler öner
- İlgili ek bilgiler sağla
- Takip soruları için hazırlıklı ol
- Workflow optimizasyonu önerilerinde bulun

Şimdi sorguyu analiz et ve en uygun yanıtı hazırla! 🚀"""

    # Web search'ün etkin olup olmadığına göre araçları belirle
    tools = [route_to_office_agent]  # Office Agent her zaman mevcut

    if web_search_enabled:
        tools.append(WebSearchTool())

    # MCP entegrasyonu ile ajanı oluştur
    agent = Agent(
        name="RAG_Assistant",
        instructions=agent_instructions,
        model="gpt-4.1", #4.1 olması gerekiyorsa çevrilsin.
        tools=tools,
    )

    return agent


# from agents import Agent, Runner, function_tool
# from typing import List
# #from aiiris_backend.agent_mcps.web_search_agent import web_search_agent
# from agents.tool import WebSearchTool
# from aiirs.aiiris_backend.agent_mcps.office_agent import office_agent

# @function_tool
# async def route_to_office_agent(task: str) -> str:
#     """Route office-related tasks to the Office Agent"""
#     result = await Runner.run(office_agent, task)
#     return result.content if hasattr(result, 'content') else str(result)


# def create_rag_agent(
#     local_context: str,
#     web_search_enabled: bool,
#     query: str,
#     instruction: str = None,
#     mcp_servers: List = None,
# ) -> Agent:

#     instruction_part = f"\n\nÖzel Talimat: {instruction}" if instruction else ""
    
#     # Web context'i dahil et
#     web_context_part = f"Elindeki WebSearchTool'unu kullanarak internette konuyla iligili araştırma yap ve " if web_search_enabled else ""

#     office_context_part = """
# 📂 Office İşlemleri:
# Office Agent'a yönlendirebileceğin görevler:
# • Word belgesi oluşturma
# • Excel dosyası oluşturma
# """ 

#     agent_instructions = f"""Local Context:
# {local_context}
# Web Context: {web_context_part if web_search_enabled else ''}

# Soru: {query}{instruction_part}


# Eğer sana bir soru sorulduysa elindeki bilgilerle soruyu yanıtla. Eğer cevap bağlamda yoksa, 
# bilmediğini söyle ve tahmin etme.
# Cevap verirken kullandığın bilginin metadatalarını 
# aşağıdaki formatta final cevabın sonuna ekle:

# Kullanılan Bilgi Metadataları:
# - Kaynak: [Source]
# - Tarih: [Date]
# - Kategori: [Category]

# Eğer senden office uygulamaları ile ilgili bir görev isteniyorsa,
# lütfen bu görevi Office Agent'a yönlendir ve onunla iletişim kur.
# {office_context_part}

# """    # Web search'ün etkin olup olmadığına göre araçları belirle
#     tools = []

#     if web_search_enabled:
#         tools.append(WebSearchTool())
#         # web_agent = web_search_agent()
#         # tools.append(web_agent.as_tool(
#         #     name="WebSearch",
#         #     description="Web üzerinde arama yapar ve ilgili sonuçları getirir.",
#         #     input_schema={
#         #         "type": "object",
#         #         "properties": {
#         #             "query": {
#         #                 "type": "string",
#         #                 "description": "Aranacak sorgu metni."
#         #             }
#         #         },
#         #         "required": ["query"]
#         #     }
#         # ))

#     # MCP entegrasyonu ile ajanı oluştur
#     agent = Agent(
#         name="RAG_Assistant",
#         instructions=agent_instructions,
#         model="gpt-4o", #4.1 olması gerekiyorsa çevrilsin.
#         tools=tools,
#     )

#     return agent
