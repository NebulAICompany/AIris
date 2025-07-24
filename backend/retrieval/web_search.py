import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from backend.llm.llm_engine import generate_answer
from typing import List


def search_web(query: str, max_links: int = 5) -> list[str]:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(
            query, region="wt-wt", safesearch="Moderate", max_results=max_links
        ):
            if "href" in r:
                results.append(r["href"])
            if len(results) >= max_links:
                break
    return results


def should_use_web_search(query: str, local_docs: List[str]) -> bool:
    # Lokal içerik özetlerini hazırla (en fazla 3 içerik, ilk 200 karakter)
    doc_summaries = []
    for i, doc in enumerate(local_docs[:3]):
        doc_con = doc.get("content", "")
        summary = doc_con[:200].replace("\n", " ").strip()
        if summary:
            print(f"Document {i+1} Summary: {summary}")
            doc_summaries.append(f"{i+1}. {summary}...")

    # Eğer lokal döküman yoksa web araması gerekli
    if not doc_summaries:
        return True

    # Prompt oluştur
    prompt = f"""Soru: {query}

Lokal içerik özetleri:
{chr(10).join(doc_summaries)}

Bu içerikler soruya yeterli mi? Yoksa güncel web bilgisi de gerekli mi? Lütfen sadece 'Evet' veya 'Hayır' olarak cevapla. Web araması gerekli ise 'Evet' yazın, değilse 'Hayır' yazın. Eğer web araması gerekli ise, lütfen neden gerekli olduğunu da belirtin."""

    # LLM'den cevap al
    answer = generate_answer(prompt).strip().lower()
    print(f"LLM Answer if web search bla bla ...: {answer}")
    # "evet" içeriyorsa web araması gerekli
    return "evet" in answer


def fetch_page_content(url: str) -> str:
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

    except Exception as e:
        return ""
    soup = BeautifulSoup(response.content, "html.parser")

    # Başlık ve ilk 2 paragraf
    title = soup.title.string.strip() if soup.title else ""
    paragraphs = [
        p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)
    ]
    content = title + "\n" if title else ""
    content += "\n".join(paragraphs[:4])

    return content[:1500]


def summarize_web_context(query: str) -> str:
    links = search_web(query)
    contents = []
    for url in links:
        text = fetch_page_content(url)
        if text:
            contents.append(text)
    return "\n---\n".join(contents)
