import base64
from nltk.tokenize import sent_tokenize


def specify_sentence(text, word):
    """
    Adds a specified word to the end of each sentence using NLTK for sentence splitting.
    
    Args:
        text (str): Input text.
        word (str): Word to append at the end of each sentence.
        
    Returns:
        str: Modified text with the word added to each sentence.
    """
    sentences = sent_tokenize(text)
    modified_sentences = []
    
    for sentence in sentences:
        if sentence.strip():  # Skip empty sentences
            # Check if sentence ends with punctuation
            if sentence[-1] in {'.', '!', '?'}:
                modified_sentence = sentence[:-1] + f" {word}" + sentence[-1]
            else:
                modified_sentence = sentence + f" {word}"
            modified_sentences.append(modified_sentence)
    
    return ' '.join(modified_sentences)


def describe_image(image_bytes, client=None):
        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen uzman bir görüntü analizcisisin. Gönderilen görseli detaylı ve anlaşılır bir şekilde Türkçe olarak açıkla.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Lütfen bu görseli detaylı ve açıklayıcı bir şekilde Türkçe olarak açıkla.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
                max_tokens=700,
            )
            description = response.choices[0].message.content
            return description

        except Exception as e:
            print(f"Error in GPT image description: {e}")
            return "Açıklama alınamadı."
        
def describe_table(table_content, client=None):
        try:
            table_text = "\n".join([" | ".join(row) for row in table_content])
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen uzman bir veri analistisin. Aşağıda bir tablo verilecek. Tabloyu inceleyip detaylıca analiz et, öne çıkan değerleri ve yorumlarını yaz.",
                    },
                    {
                        "role": "user",
                        "content": f"Tablo:\n{table_text}\n\nLütfen bu tabloyu detaylı yorumla:",
                    },
                ],
                max_tokens=800,
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"Error in GPT table description: {e}")
            return "Tablo açıklaması alınamadı."

def describe_chart(self, chart_data):
    """
    Grafik verilerini GPT-4'e göndererek Türkçe açıklama üretir.
    Args:chart_data (list): Grafikle ilgili verilerin listesi (başlık, seri adları, değerler, kategoriler)
    Returns:str: GPT tarafından oluşturulan Türkçe grafik açıklaması
    """
    try:
        # Grafik verilerini metin formatında birleştir
        chart_text = "\n".join(chart_data)
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sen bir veri analizi uzmanısın. Aşağıda verilen grafik bilgilerini analiz edip "
                        "anlaşılır ve detaylı bir Türkçe özet oluştur. Grafiğin türünü, gösterdiği verileri, "
                        "eğilimleri ve dikkat çeken noktaları açıkla. Grafik başlığına özellikle dikkat et."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Bu grafik verilerini analiz edip Türkçe açıklama yapar mısın?\n\n{chart_text}",
                },
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        description = response.choices[0].message.content
        return description
    except Exception as e:
        print(f"Error in GPT chart description: {e}")
        return "Grafik açıklaması alınamadı."