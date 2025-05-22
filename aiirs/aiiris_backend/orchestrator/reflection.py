from typing import Callable
from aiiris_backend.llm.llm_engine import generate_answer

def reflect_and_retry(prompt: str, initial_answer: str, retry_fn: Callable[[], str], max_retries: int = 2) -> str:
    
    current_answer = initial_answer
    retry_count = 0
    while retry_count < max_retries:
        reflection_prompt = f"""
        Orijinal Soru : {prompt}
        
        Verilen Cevap : {current_answer}
        
        Bu cevap orijinal soruya tam, doğru ve kapsamlı bir yanıt veriyor mu? 
        Sadece "Evet" veya "Hayır" şeklinde cevap ver.
        """    
        
        reflection = generate_answer(reflection_prompt).strip().lower()
        
        if reflection == "evet":
            return current_answer
        else:
            retry_count += 1
            if retry_count < max_retries:
                current_answer = retry_fn()
                
    return current_answer