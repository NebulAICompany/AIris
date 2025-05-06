import os
import pdfplumber
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
import json
import re
from pathlib import Path

class UploadPipeline:
    def __init__(
            self, pdf_path: str, azure_endpoint: str = None, azure_key:str =None):
        
        self.pdf_path = pdf_path
        self.azure_endpoint = azure_endpoint or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.azure_key = azure_key or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.device = "cpu"
        self.picprocessor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)


        if not self.azure_endpoint or not self.azure_key:
            raise ValueError(
                "Azure Document Intelligence credentials not provided. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY "
                "environment variables or pass them as parameters."
            )
        
        self.document_analysis_client = DocumentAnalysisClient( endpoint = self.azure_endpoint, credential = AzureKeyCredential(self.azure_key) )

    def run(self):

        with open(self.pdf_path, "rb") as f:
            poller = self.document_analysis_client.begin_analyze_document(
                "prebuilt-layout", document=f
            )
        result = poller.result() #pdf i azurea gönderiyruz
        
        extracted_text = {"content": result.content,"pages": []}

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in result.pages:
                page_data = {
                    "page_number": page.page_number,
                    "blocks": []
                }

                elements = []

                for line in page.lines:
                    y_pos = min([point.y for point in line.bounding_polygon])
                    elements.append({
                        "type": "text",
                        "y":y_pos,
                        "content":line.content
                    })

                images_on_current_page = [img for img in result.images if img.page_number == page.page_number]

                for img in images_on_current_page:
                    y_pos = min([point.y for point in img.bounding_polygon])
                    the_image = self.extract_image_from_pdf_by_coords(pdf, page.page_number -1, img)
                    caption = self.run_blip_model(the_image)
                    elements.append({
                        "type": "picture",
                        "y": y_pos,
                        "description": caption
                    })

                tables_on_page = [table for table in result.tables if table.page_number == page.page_number]
                for table in tables_on_page:
                    for cell in table.cells:
                        y_pos = min([point.y for point in cell.bounding_polygon])
                        elements.append({
                            "type": "te"
                        })

                elements.sort(key=lambda e: e["y"])

                for elem in elements:
                    if elem["type"] == "text":
                        page_data["blocks"].append({
                            "lines": [{
                                "words": [{"value": word} for word in elem["content"].split()]
                            }]
                        })
                    elif elem["type"] == "picture":
                        page_data["blocks"].append({
                        "type": "picture",
                        "description": elem["description"]
                        })
                
                extracted_text["pages"].append(page_data)
        
        
        return extracted_text
    
    def clean_text(text):
        # Satır sonlarını boşluk yap
        text = text.replace('\n', ' ')
        # Birden fazla boşluğu tek boşluk yap
        text = re.sub(r'\s+', ' ', text)
        # Baş ve sondaki boşlukları sil
        text = text.strip()
        # İzin verilen karakterler:
        # Harfler, sayılar, Türkçe karakterler, noktalama işaretleri ve finans sembolleri
        text = re.sub(r'[^a-zA-Z0-9çÇşŞıİğĞöÖüÜ.,:;!?()\-\'"%$€₺+*/=#&<>]', '', text)
        return text

    def extract_image_from_pdf_by_coords(self, pdf, page_index, img_object):
        page = pdf.pages[page_index]
        x0 = min([p.x for p in img_object.bounding_polygon])
        x1 = max([p.x for p in img_object.bounding_polygon])
        y0 = min([p.y for p in img_object.bounding_polygon])
        y1 = max([p.y for p in img_object.bounding_polygon])

        page_height = page.height
        box_to_crop = (x0, page_height - y1, x1, page_height - y0)

        cropped_img = page.to_image(resolution = 300).original.crop(box_to_crop)

        return cropped_img
    
    def save(self, extracted_text: dict, save_path: str = None):
        if save_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            save_path = str(base_dir / "uploads")

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        output_file = os.path.join(save_path, os.path.basename(self.pdf_path).replace(".pdf", "_ocr.txt"))

        with open(output_file, "w", encoding= "utf-8") as f:
            for page_num, page in enumerate(extracted_text["pages"], start=1):
                f.write(f"\n--- Page {page_num} ---\n")
                for block in page["blocks"]:
                    # Eğer block bir metin bloğuyse
                    if "lines" in block:
                        for line in block["lines"]:
                            f.write(" ".join(word["value"] for word in line["words"]) + "\n")
                    # Eğer block bir resim açıklamasıysa
                    elif block.get("type") == "picture":
                        f.write(f"[Image Caption]: {block['description']}\n")
        print(f"\n✅ Text extraction complete! Saved to '{output_file}'")

    def save_as_json(self, extracted_text: dict, save_path: str = None):
        if save_path is None:
            # Use relative path if not specified
            base_dir = Path(__file__).resolve().parent.parent
            save_path = str(base_dir / "uploads")

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        output_file = os.path.join(
            save_path, os.path.basename(self.pdf_path).replace(".pdf", "_ocr.json")
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(extracted_text, f, indent=4, ensure_ascii=False)

        print(f"\n✅ JSON extraction complete! Saved to '{output_file}'")

    
import sys
sys.stdout.reconfigure(encoding='utf-8')

def main():
    # Azure Document Intelligence kimlik bilgileri (environment variables'tan alınacak)
    AZURE_ENDPOINT = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    AZURE_KEY = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    print("🔑 Azure kimlik bilgileri kontrol ediliyor...")
    # Test edilecek PDF dosyasının yolu
    pdf_path = "the_file.pdf"  # Kendi PDF dosyanızın yolunu belirtin
    
    if not os.path.exists(pdf_path):
        print(f"❌ Hata: {pdf_path} dosyası bulunamadı!")
        return
    
    print(f"📄 PDF dosyası bulundu: {pdf_path}")
    # Pipeline'ı başlat
    try:
        print("🚀 Azure Document Intelligence başlatılıyor...")
        pipeline = UploadPipeline(
            pdf_path=pdf_path,
            azure_endpoint=AZURE_ENDPOINT,
            azure_key=AZURE_KEY
        )
        
        print("🔍 PDF analiz ediliyor...")
        extracted_data = pipeline.run()
        
        # Sonuçları kaydet
        output_dir = Path(__file__).parent / "outputs"
        pipeline.save(extracted_data, save_path=str(output_dir))
        pipeline.save_as_json(extracted_data, save_path=str(output_dir))
        
        print("\n✨ Analiz sonuçları:")
        print(f"- Toplam sayfa: {len(extracted_data['pages'])}")
        
        # İlk sayfanın özetini göster
        if extracted_data['pages']:
            first_page = extracted_data['pages'][0]
            print(f"\n📄 Sayfa 1 Özeti:")
            print(f"- Metin blokları: {len([b for b in first_page['blocks'] if 'lines' in b])}")
            print(f"- Resimler: {len([b for b in first_page['blocks'] if b.get('type') == 'picture'])}")
            
            # İlk resim açıklamasını göster (varsa)
            pictures = [b for b in first_page['blocks'] if b.get('type') == 'picture']
            if pictures:
                print(f"- Örnek resim açıklaması: '{pictures[0]['description']}'")
                
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")

if __name__ == "__main__":
    main()