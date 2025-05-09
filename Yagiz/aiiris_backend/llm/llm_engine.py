import os 
import time
from openai import OpenAI
from aiiris_backend.monitoring.metrics import llm_duration_seconds


client = OpenAI(api_key="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")

def generate_answer(prompt: str) -> str:
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Lütfen sadece verilen bağlama sadık kalarak yanıt ver."},
                      {"role": "user", "content": prompt}
                      ],
            temperature=0.3,
        )
        answer = response.choices[0].message.content.strip()
        duration = time.time() - start_time
        llm_duration_seconds.observe(duration)
        
        return answer
    except Exception as e:
        return f"LLM yanıtı alınamadı: {str(e)}"
