def create_rag_prompt(context: str, query: str, instruction:str = None) -> str:
    """
    Creates a RAG prompt by combining retrieved context with user query.
    
    Args:
        context (str): Retrieved documents joined as text
        query (str): User's question
        
    Returns:
        str: Formatted prompt for LLM
    """
    instruction_text = ""
    if instruction : 
        instruction_text = f"\n\nÖzel Talimat: {instruction}"
    prompt = f"""Context:
{context}

Soru: {query}{instruction_text}

Yukarıdaki bağlam bilgisine dayanarak, soruyu yanıtla. Eğer cevap bağlamda yoksa, 
bilmediğini söyle ve tahmin etme. Cevap verirken kullandığın bilginin metadatalarını 
aşağıdaki formatta final cevabın sonuna ekle:

Kullanılan Bilgi Metadataları:
- Kaynak: [Source]
- Tarih: [Date]
- Kategori: [Category]"""
    
    return prompt


