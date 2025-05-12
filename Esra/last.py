from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os
import nltk
import json

# NLTK punkt yükleme
nltk.download('punkt')

# Azure bilgileri
endpoint = "YOUR_ENDPOINT"
key = "YOUR_KEY"

client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# PDF dosyası yolu
pdf_path = "financial-report.pdf"
source_file = os.path.basename(pdf_path)

results = []

# PDF’yi aç ve Azure’a gönder
with open(pdf_path, "rb") as f:
    poller = client.begin_analyze_document("prebuilt-layout", document=f)
    result = poller.result()

# Sayfa sayısı
page_number = 0

# Sayfaları tek tek işle
for page in result.pages:
    page_number += 1

    # Metinleri blok blok al
    for line in page.lines:
        sentences = nltk.sent_tokenize(line.content)
        for sentence_number, sentence in enumerate(sentences):
            metadata = {
                "content": sentence,
                "page_number": page_number,
                "type": "sentence",
                "bbox": [{"x": p.x, "y": p.y} for p in line.bounding_polygon],
                "source_file": source_file
            }
            results.append(metadata)

    # Tabloları al
    for table in result.tables:
        table_content = []
        for cell in table.cells:
            table_content.append({
                "text": cell.content,
                "row_index": cell.row_index,
                "column_index": cell.column_index
            })

        metadata = {
            "content": table_content,
            "page_number": page_number,
            "type": "table",
            "bbox": None,  # Azure Form Recognizer’da cell bazında var, table genel koordinatını ayrıca hesaplayabiliriz
            "source_file": source_file
        }
        results.append(metadata)

    # Resimleri al
    for image in page.images:
        metadata = {
            "content": f"Image at page {page_number}",
            "page_number": page_number,
            "type": "image",
            "bbox": [{"x": p.x, "y": p.y} for p in image.bounding_polygon],
            "source_file": source_file
        }
        results.append(metadata)

# Sonuçları JSON olarak kaydet
with open("azure_extracted_content.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

print(f"{len(results)} içerik kaydedildi.")
