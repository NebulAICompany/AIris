def create_rag_prompt(context: str, query: str) -> str:
    """
    Creates a RAG prompt by combining retrieved context with user query.
    
    Args:
        context (str): Retrieved documents joined as text
        query (str): User's question
        
    Returns:
        str: Formatted prompt for LLM
    """
    prompt = f"""Context:
{context}

Soru: {query}

Yukarıdaki bağlam bilgisine dayanarak, soruyu yanıtla. Eğer cevap bağlamda yoksa, 
bilmediğini söyle ve tahmin etme."""
    
    return prompt


