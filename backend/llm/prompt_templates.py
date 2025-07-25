from agents import Agent
from typing import List
from agents.tool import WebSearchTool
from backend.core.agents import office_agent, alpha_vantage_agent

# Import our custom wolfram function tool
from backend.core.tools.api import wolfram_alpha_query


def create_rag_agent(
    local_context: str,
    web_search_enabled: bool,
    query: str,
    instruction: str = None,
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

    office_agent_tool = office_agent.as_tool(
        tool_name="office_operations",
        tool_description="""Use this tool for Microsoft Office operations including:
        - Creating Excel workbooks from structured data
        - Generating Word documents with custom content
        - Document processing and format conversion
        - Any task requiring Word or Excel functionality""",
    )

    alpha_vantage_tool = alpha_vantage_agent.as_tool(
        tool_name="financial_data_analysis",
        tool_description="""Use this tool for financial data analysis including:
        - Stock quotes and company information
        - Cryptocurrency rates and analysis
        - Historical price data and time series
        - Option chain data and technical analysis
        - Market trends and volatility analysis
        - Any financial data query or analysis""",
    )

    tools = [office_agent_tool, alpha_vantage_tool]
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
2. **Akıllı Yönlendirme:** Specialized agentları doğru kullan
3. **Kapsamlı Yanıtlama:** Mevcut bilgilerle detaylı ve doğru yanıtlar ver
4. **Kaynak Belgeleme:** Kullandığın bilgilerin metadatalarını sağla

🔧 **İşlem Protokolleri:**

**🏢 Office İşlemleri İçin:**
Aşağıdaki durumlardan herhangi birinde office_operations aracını kullan:
- Word belgesi oluşturma ve düzenleme
- Excel dosyası oluşturma ve veri işleme
- Tablo verilerinden Excel dosyası çıkarma
- Belge formatı dönüştürme
- Herhangi bir Microsoft Office uygulaması gerektiren işlem

**💰 Finansal Veri Analizi İçin:**
Aşağıdaki durumlardan herhangi birinde financial_data_analysis aracını kullan:
- Hisse senedi fiyatları ve kotasyonları
- Şirket finansal bilgileri (sektör, piyasa değeri)
- Kripto para kurları ve analizi
- Tarihsel fiyat verileri ve zaman serileri
- Opsiyon zinciri verileri
- Teknik analiz ve piyasa trendleri
- Herhangi bir finansal veri sorgusu veya analizi

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
- Specialized agentları doğru işlev için kullan
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
