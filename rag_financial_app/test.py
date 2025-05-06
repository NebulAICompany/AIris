from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
import os

# Try to import OpenAI embeddings first, fall back to HuggingFace
try:
    from langchain_openai import OpenAIEmbeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key="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")
    print("Using OpenAI embeddings")
except (ImportError, Exception):
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        print("Using HuggingFace embeddings")
    except (ImportError, Exception) as e:
        print(f"Failed to load embeddings: {e}")
        exit(1)

# Sample financial documents for testing
sample_docs = [
    Document(
        page_content="Enflasyon oranları aylık %1,2 artarak yıllık %12,5 seviyesine ulaştı. Bu durum, merkez bankasının faiz kararlarını etkileyebilir.",
        metadata={"source": "financial_news_1.txt", "date": "2023-10-15", "category": "economy"}
    ),
    Document(
        page_content="Türkiye Cumhuriyet Merkez Bankası, politika faizini %25 seviyesinde tutma kararı aldı. Piyasalar bu kararı olumlu karşıladı.",
        metadata={"source": "financial_news_2.txt", "date": "2023-10-20", "category": "central_bank"}
    ),
    Document(
        page_content="Türk Lirası, dolar karşısında %2 değer kazandı. Bu durum, ihracatçıları olumsuz etkileyebilir.",
        metadata={"source": "financial_news_3.txt", "date": "2023-10-22", "category": "currency"}
    ),
    Document(
        page_content="Borsa İstanbul, günü %1,5 yükselişle kapattı. Bankacılık sektörü hisseleri en çok değer kazanan hisseler oldu.",
        metadata={"source": "financial_news_4.txt", "date": "2023-10-23", "category": "stock_market"}
    ),
    Document(
        page_content="Kripto para piyasası son 24 saatte %5 değer kaybetti. Bitcoin 60.000 dolar seviyesinin altına geriledi.",
        metadata={"source": "financial_news_5.txt", "date": "2023-10-24", "category": "crypto"}
    ),
    Document(
        page_content="Altın fiyatları, jeopolitik gerginliklerin artmasıyla yükselişe geçti. Gram altın 1.100 TL'yi aştı.",
        metadata={"source": "financial_news_6.txt", "date": "2023-10-25", "category": "commodities"}
    ),
    Document(
        page_content="Cari açık beklentilerin üzerinde artarak 3.5 milyar dolara ulaştı. Bu durum, ekonomik dengeleri olumsuz etkileyebilir.",
        metadata={"source": "financial_news_7.txt", "date": "2023-10-26", "category": "economy"}
    ),
    Document(
        page_content="Yabancı yatırımcılar, son hafta içinde Türkiye'den 250 milyon dolar çıkış yaptı. Bu durum, piyasalarda volatiliteyi artırabilir.",
        metadata={"source": "financial_news_8.txt", "date": "2023-10-27", "category": "investments"}
    ),
]

# Create the vector store directory if it doesn't exist
vector_store_path = "aiiris_backend/retrieval/vectorstore"
os.makedirs(vector_store_path, exist_ok=True)

# Create and save the vector store
vectorstore = FAISS.from_documents(documents=sample_docs, embedding=embeddings)
vectorstore.save_local(folder_path=vector_store_path)

print(f"Test vector store created and saved to {vector_store_path}")
print(f"Number of documents: {len(sample_docs)}")

# Test a simple query to verify it works
query = "merkez bankası faiz kararları"
results = vectorstore.similarity_search(query=query, k=2)
print("\nTest query results:")
for doc in results:
    print(f"- {doc.page_content}")
    print(f"  Source: {doc.metadata['source']}, Category: {doc.metadata['category']}")