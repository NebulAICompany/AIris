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
    return result.content if hasattr(result, "content") else str(result)


# Import our custom wolfram function tool
from aiiris_backend.agents.wolfram_alpha_tool import wolfram_alpha_query


def create_rag_agent(
    local_context: str,
    web_search_enabled: bool,
    query: str,
    instruction: str = None,
    mcp_servers: List = None,
    wolfram_enabled: bool = False,
    conversation_history: List = None,
) -> Agent:

    instruction_part = f"\n\nÖzel Talimat: {instruction}" if instruction else ""

    # Web context'i dahil et
    web_context_part = (
        f"Elindeki WebSearchTool'unu kullanarak internette konuyla ilgili araştırma yap ve "
        if web_search_enabled
        else ""
    )

    # Conversation history'i formatla
    conversation_context_part = ""
    if conversation_history and len(conversation_history) > 0:
        conversation_context_part = "\n💬 **Sohbet Geçmişi:**\n"
        for i, msg in enumerate(conversation_history[-5:]):  # Son 5 mesajı göster
            role = "🙋 Kullanıcı" if msg["role"] == "user" else "🤖 Asistan"
            conversation_context_part += f"{role}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}\n"
        conversation_context_part += "\n"

    tools = [route_to_office_agent]
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

Elindeki wolfram_alpha_query fonksiyonunu kullanarak matematiksel hesaplamalar, bilimsel veriler veya istatistiksel analizler yap
"""
        if wolfram_enabled
        else ""
    )

    agent_instructions = f"""🤖 Sen gelişmiş bir RAG (Retrieval-Augmented Generation) Asistanısın. 
**Wolfram Yönergeleri:**
{wolfram_instructions}

📊 **Yerel Bağlam Bilgileri:**
{local_context}

🔍 **Web Arama Durumu:** {web_context_part}
{conversation_context_part}
❓ **Mevcut Sorgu:**
{query}{instruction_part}

📋 **Görev Tanımın ve Sorumlulukların:**

🎯 **Ana Görevler:**
1. **Bilgi Analizi:** Sorguyu analiz et ve hangi kaynakları kullanman gerektiğini belirle
2. **Akıllı Yönlendirme:** Office işlemleri için route_to_office_agent fonksiyonunu kullan
3. **Kapsamlı Yanıtlama:** Mevcut bilgilerle detaylı ve doğru yanıtlar ver
4. **Kaynak Belgeleme:** Kullandığın bilgilerin metadatalarını sağla

🔧 **İşlem Protokolleri:**

**🏢 Office İşlemleri İçin:**
Aşağıdaki durumlardan herhangi birinde route_to_office_agent'ı kullan:
- "Word belgesi oluştur"
- "Excel dosyası oluştur"
- Herhangi bir office uygulaması gerektiren işlem olursa route_to_office_agent fonksiyonunu çağır


📐 **Kalite Standartları:**
- ✅ Doğru ve güncel bilgi sağla
- ✅ Kaynaklarını şeffaf bir şekilde belge
- ✅ Belirsizlikleri açıkça ifade et
- ✅ Kullanıcı dostu ve anlaşılır dil kullan
- ✅ Yapılandırılmış ve organize yanıtlar ver

📊 **Yanıt Formatı:**
Her yanıtının sonunda kullandığın kaynakların metadatalarını aşağıdaki şekilde göster:

```
🗂️ Kullanılan Bilgi Metadataları:
- 📂 Kaynak: (Gerçek kaynak dosya adı)
- 📅 Tarih: (Dokümanın tarihi varsa)
- 🏷️ Kategori: (İçerik kategorisi)
```

NOT: Eğer herhangi bir bilgi mevcut değilse o satırı atlayabilirsin. Placeholder veya boş değerler ([...], None, vb.) kullanma.

**Kritik Kurallar:**
- Bilmediğin konularda spekülasyon yapma
- Office işlemlerini kendın yapmaya çalışma, Office Agent'a yönlendir
- Her zaman güvenilir kaynakları tercih et
- Kullanıcının gizliliğini ve veri güvenliğini koru


Şimdi sorguyu analiz et ve en uygun yanıtı hazırla! """

    agent = Agent(
        name="RAG_Assistant",
        instructions=agent_instructions,
        model="gpt-4.1",
        tools=tools,
    )

    return agent
