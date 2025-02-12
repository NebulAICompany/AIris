from langchain_community.vectorstores import FAISS
from openai import OpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
import os


class QueryPipeline:
    def __init__(self, query: str, vectorstore_path: str):
        self.query = query
        self.vectorstore_path = vectorstore_path

        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set")

    def __find_similar_chunks(self):
        vectorstore = FAISS.load_local(
            f"{self.vectorstore_path}",
            embeddings=OpenAIEmbeddings(model="text-embedding-3-large"),
            allow_dangerous_deserialization=True,
        )
        chunks_query_retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        similar_chunks = chunks_query_retriever.invoke(self.query)
        return similar_chunks

    def __generate_prompt(self):
        relevant_chunks = "\n".join(
            [chunk.page_content for chunk in self.__find_similar_chunks()]
        )
        prompt = f"""Aşağıdaki verilen context'i KESİNLİKLE kullanarak, soruya **TÜM CEVABI MARKDOWN SYNTAXI İLE** formatla:
        - Başlıkları `##` ile oluştur
        - **Kalın** ve *italik* metin kullan
        - Listeler için `-` veya `1.` kullan
        - Vereceğin cevaplar için asla * işareti kullanmadan önce - veya 1. kullanma gibi liste işaretlerini kullanma. * işareti kullanacağın yerde bunlar olmasın.
        - Context dışına çıkma!

        Context:
        {' '.join(relevant_chunks)}

        Soru: {self.query}

        Cevap:"""
        return prompt

    def generate_response(self):
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # GPT-4 modelini kullan (daha iyi Markdown desteği için)
            messages=[
                {
                    "role": "system",
                    "content": "TÜM CEVAPLARINI MARKDOWN İLE YAZ. Format: ## Başlık, **kalın**, *italik*, - liste.",
                },
                {"role": "user", "content": self.__generate_prompt()},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    # def save(self, similar_chunks: dict, save_path: str):
    #     if save_path is None:
    #         save_path = "query_results.txt"
    #     with open(save_path, "w", encoding="utf-8") as f:
    #         for chunk in similar_chunks:
    #             f.write(f"Chunk: {chunk['text']}\n")
    #             f.write(f"Similarity: {chunk['score']}\n\n")

    #     print(f"\n✅ Query complete! Saved to '{save_path}'")


import os

os.environ["OPENAI_API_KEY"] = (
    "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"  # Replace with your OpenAI key
)
