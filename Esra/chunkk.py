import os
import json
from pathlib import Path
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings  # veya varsa kendi embedding class'ını koyabilirsin
os.environ["OPENAI_API_KEY"] = "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"

class VectorStorePipeline:
    def __init__(self):
        # Embedding modeli (OpenAI veya senin kullandığın embedding)
        self.embeddings = OpenAIEmbeddings(key=os.environ["OPENAI_API_KEY"])
        print("Embeddings initialized")
        # SemanticChunker ayarları
        self.text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=80,
        )

    def run(self, uploads_path: str, save_path: str = None):
        try:
            # JSON OCR dosyalarını bul
            files = [
                f for f in os.listdir(uploads_path) if f.endswith("_ocr.json")
            ]
            if not files:
                print("No JSON OCR files found in uploads directory")
                return

            # Textleri topla
            extracted_texts = []
            total_text_length = 0

            for file in files:
                file_path = os.path.join(uploads_path, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        text_items = [item["content"] for item in data if item["type"] == "text"]
                        extracted_texts.extend(text_items)
                        total_text_length += sum(len(t) for t in text_items)
                        print(f"Read {len(text_items)} text items from {file}")
                except Exception as e:
                    print(f"Error reading file {file}: {str(e)}")

            if not extracted_texts:
                print("No valid text content found in JSON files")
                return

            print(f"Total text length: {total_text_length} characters")

            # Semantic chunk’lara böl
            docs = self.text_splitter.create_documents(extracted_texts)

            if not docs:
                print("Warning: No chunks created. Text may be too short or uniform.")
                return

            print(f"\n✅ Text split into {len(docs)} semantic chunks")

            # Chunk'ları JSON olarak kaydet
            self.save_chunks_as_json(docs, uploads_path, save_path)

        except Exception as e:
            print(f"Error during text processing: {str(e)}")

    def save_chunks_as_json(self, docs, uploads_path: str, save_path: str = None):
        try:
            save_dir = Path(save_path) if save_path else Path(uploads_path)
            save_dir.mkdir(parents=True, exist_ok=True)

            output_file = save_dir / "semantic_chunks.json"

            chunk_data = []
            for i, doc in enumerate(docs):
                chunk_data.append({
                    "chunk_id": i,
                    "content": doc.page_content
                })

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=4)

            print(f"\n✅ Semantic chunks saved to {output_file}")

        except Exception as e:
            print(f"Error saving chunks as JSON: {str(e)}")

if __name__ == "__main__":
    # Örnek kullanım
    pipeline = VectorStorePipeline()
    pipeline.run(uploads_path="uploads", save_path="output")