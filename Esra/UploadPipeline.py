import io
from pathlib import Path
from PIL import Image
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import os
import json
import fitz
import nltk
from transformers import BlipProcessor, BlipForConditionalGeneration

class UploadPipeline:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.device = "cpu"
        self.azure_endpoint = "https://docaiiriswork.cognitiveservices.azure.com/"
        self.azure_key = "1Ab3Lpd2qh8sEtMCOZZLoW6QFqtBOVOYgwzcbo8I9BxBY9J3vtEcJQQJ99BEACYeBjFXJ3w3AAALACOG22i3"
        self.picprocessor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast = True)
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        self.source_file = os.path.basename(pdf_path)

        if not self.azure_endpoint or not self.azure_key:
            raise ValueError(
                "Azure Document Intelligence credentials not provided. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY "
                "environment variables or pass them as parameters."
            )
        self.document_analysis_client = DocumentAnalysisClient( endpoint = self.azure_endpoint, credential = AzureKeyCredential(self.azure_key) )
    
    def run(self):
        save_dir = Path(__file__).resolve().parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_stem = Path(self.pdf_path).stem
        output_file = save_dir / f"{pdf_stem}_txt.txt"

        with open(output_file, 'w', encoding='utf-8') as dosya:
                results = []
                pdf = fitz.open(self.pdf_path)
                with open(self.pdf_path, "rb") as f:
                    poller = self.document_analysis_client.begin_analyze_document("prebuilt-layout", document=f)
                    result = poller.result()

                num_pages = len(pdf)
                print("Starting PDF analysis...")
                for page_num in range(num_pages):
                    page = pdf.load_page(page_num)
                    dosya.write(f"\n------Page {page_num + 1}------\n\n")
                    # Paragraphs
                    page_paragraphs = [p for p in result.paragraphs if p.bounding_regions and p.bounding_regions[0].page_number == page_num + 1]
                    for paragraph in page_paragraphs:
                        sentences = nltk.sent_tokenize(paragraph.content)
                        for sentence in sentences:
                            metadata = {
                                "content": sentence,
                                "page_number": page_num,  # fix: sıfırdan başlayan index
                                "type": "text",
                                "source_file": self.source_file
                            }
                            dosya.write(sentence)
                            dosya.write(" ")
                            results.append(metadata)

                    # Tables
                    page_tables = [t for t in result.tables if t.bounding_regions and t.bounding_regions[0].page_number == page_num + 1]
                    table_counter = 1
                    for table in page_tables:
                        dosya.write(f"\n[Table {table_counter}]\n")
                        table_content = []
                        for cell in table.cells:
                            table_content.append({
                                "text": cell.content,
                                "row_index": cell.row_index,
                                "column_index": cell.column_index
                            })
                            dosya.write(f"[{cell.row_index},{cell.column_index}]: {cell.content}\n")
                        metadata = {
                            "content": table_content,
                            "page_number": page_num,
                            "type": "table",
                            "bbox": None,
                            "source_file": self.source_file
                        }
                        table_counter += 1
                        results.append(metadata)

                    # Images
                    images = page.get_images(full=True)
                    for img_index, img in enumerate(images):
                        try:
                            img_xref = img[0]
                            img_bbox = page.get_image_bbox(img)

                            base_image = pdf.extract_image(img_xref)
                            image_bytes = base_image["image"]

                            description = self.run_blip_model(Image.open(io.BytesIO(image_bytes)))
                            dosya.write(f"\n[Image {img_index + 1}]\n")
                            dosya.write(f"Description: {description}\n")
                            metadata = {
                                "type": "image",
                                "coordinates": {
                                    "x0": round(img_bbox.x0, 2),
                                    "y0": round(img_bbox.y0, 2),
                                    "x1": round(img_bbox.x1, 2),
                                    "y1": round(img_bbox.y1, 2)
                                },
                                "description": description,
                                "page_number": page_num + 1,
                                "source_file": self.source_file,
                                "image_data": {
                                    "format": base_image["ext"],
                                    #"bytes": base_image["image"],
                                    "size": len(base_image["image"]),
                                }
                            }
                            results.append(metadata)
                        except Exception as e:
                            print(f"Error processing image {img_index}: {e}")
                            continue
        # self.save_as_json(results)

    def save_as_json(self, results: dict, pretty_print: bool = True, save_path: str = None) -> str:
        if not results:
            raise ValueError("No results to save - empty input detected")
        
        # Prepare save directory
        save_dir = Path(save_path) if save_path else Path(__file__).resolve().parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_stem = Path(self.pdf_path).stem
        output_file = save_dir / f"{pdf_stem}_ocr.json"
        
        try:
            # Custom JSON encoder for handling bytes
            class BytesEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, bytes):
                        return obj.decode('latin1')  # For image byte data
                    return super().default(obj)
            
            # Write with error handling
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(
                    results,
                    f,
                    ensure_ascii=False,
                    indent=4 if pretty_print else None,
                    cls=BytesEncoder
                )
            
            # Print summary
            stats = {
                'total_items': len(results),
                'text_items': sum(1 for x in results if x['type'] == 'text'),
                'tables': sum(1 for x in results if x['type'] == 'table'),
                'images': sum(1 for x in results if x['type'] == 'image'),
                'file_size': f"{os.path.getsize(output_file)/1024:.1f} KB"
            }
            
            print(f"✅ Successfully saved {stats['total_items']} items to:\n{output_file}")
            print("📊 Stats:", json.dumps(stats, indent=2))
            
            return str(output_file)
        
        except (IOError, TypeError, json.JSONEncodeError) as e:
            error_msg = f"JSON save failed: {str(e)}"
            if isinstance(e, TypeError) and 'bytes' in str(e):
                error_msg += "\n💡 Tip: Image byte data may need special handling"
            raise OSError(error_msg) from e

    def run_blip_model(self, image):
        inputs = self.picprocessor(images=image, return_tensors="pt").to(self.device)
        out = self.blip_model.generate(**inputs, max_new_tokens=50)
        caption = self.picprocessor.decode(out[0], skip_special_tokens=True)
        #print("the caption is: ", caption)
        return caption
    

def main():
    # pdf_path = "the_file.pdf"  # Kendi PDF dosyanızın yolunu belirtin
    pdf_path = "Esra/pdf_file.pdf"
    #pdf_path = "belge.pdf"
    #pdf_path = "file.pdf"
    #pdf_path = "image.pdf"
    if not os.path.exists(pdf_path):
        print(f"❌ Hata: {pdf_path} dosyası bulunamadı!")
        return
    
    print(f"📄 PDF dosyası bulundu: {pdf_path}")
    # Pipeline'ı başlat
    try:
        pipeline = UploadPipeline( pdf_path=pdf_path )
        
        print("🔍 PDF analiz ediliyor...")
        extracted_data = pipeline.run()
        
        #pipeline.save_as_json(extracted_data)
        
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")


if __name__ == "__main__":
    main()