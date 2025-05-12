import os
import io
import fitz  # PyMuPDF
from transformers import BlipProcessor, BlipForConditionalGeneration
import layoutparser as lp
import re
from pathlib import Path
import warnings
from PIL import Image
warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")

class UploadPipeline:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.device = "cpu"
        self.picprocessor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast = True)
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        self.metadata = {}

    def run(self):
        extracted_text = {"pages": []}
        pdf = fitz.open(self.pdf_path)
        

        for page_num in range(2,3):
            page = pdf.load_page(page_num)
            page_data = {
                "page_number": page_num + 1,
                "blocks": []
            }

            # Extract text blocks with precise coordinates ("blocks" sildim")
            text_blocks = page.get_text("blocks", sort=True)  # sort=True maintains reading order
            for block in text_blocks:
                
                # Handle variable block formats across versions
                if len(block) == 6:  # Older versions (x0,y0,x1,y1,text,block_no)
                    x0, y0, x1, y1, text, block_no = block
                    block_type = 0  # Assume text block
                elif len(block) == 7:  # Newer versions (+block_type)
                    x0, y0, x1, y1, text, block_no, block_type = block
                else:
                    print(f"Unexpected block format: {block}")
                    continue
                
                # Skip non-text blocks (images are handled separately)
                #if block_type != 0:  # 0 indicates text blocks
                    #continue
                    
                page_data["blocks"].append({
                    "type": "text",
                    "coordinates": {
                        "x0": round(x0, 2),
                        "y0": round(y0, 2),
                        "x1": round(x1, 2),
                        "y1": round(y1, 2)
                    },
                    "content": text.strip(),
                    "lines": [{
                        "words": [{"value": word, "bbox": [x0, y0, x1, y1]} for word in text.split()],
                        "bbox": [x0, y0, x1, y1]
                    }]
                })

            # Extract and process images
            images = page.get_images(full=True)
            
            for img_index, img in enumerate(images):
                try:
                    #image = self.extract_image_from_pdf_by_coords(pdf, page_num, img_index)
                    #description = self.run_blip_model(image)
                    
                    # Get image position (approximate)
                    img_xref = img[0]
                    img_bbox = page.get_image_bbox(img)
                    
                    base_image = pdf.extract_image(img_xref)
                    image_bytes = base_image["image"]
                    
                    description = self.run_blip_model(Image.open(io.BytesIO(image_bytes)))

                    page_data["blocks"].append({
                        "type": "image",
                        "coordinates": {
                            "x0": round(img_bbox.x0, 2),
                            "y0": round(img_bbox.y0, 2),
                            "x1": round(img_bbox.x1, 2),
                            "y1": round(img_bbox.y1, 2)
                        },
                        "description": description,
                        "image_data": {
                            "format": base_image["ext"],
                            "bytes": base_image["image"],
                            "size": len(base_image["image"]),
                        }
                    })

                    # Save image if needed
                    #from PIL import Image
                    #import io

                    #img = Image.open(io.BytesIO(content["image_data"]["bytes"]))
                    #img.save(f"image_{page_num}_{index}.{content['image_data']['format']}")


                except Exception as e:
                    print(f"Error processing image {img_index} on page {page_num}: {e}")
                    continue

            # Advanced sorting - first by y0, then by x0
            page_data["blocks"].sort(key=lambda b: (round(b["coordinates"]["y0"],1), # Group items with ~same y position
                                                    b["coordinates"]["x0"]))# Sort horizontally within y group
            
            extracted_text["pages"].append(page_data)

        return extracted_text

    def run_blip_model(self, image):
        inputs = self.picprocessor(images=image, return_tensors="pt").to(self.device)
        out = self.blip_model.generate(**inputs, max_new_tokens=50)
        caption = self.picprocessor.decode(out[0], skip_special_tokens=True)
        #print("the caption is: ", caption)
        return caption

    
    def save(self, extracted_text: dict, save_path: str = None):
        if save_path is None:
            base_dir = Path(__file__).resolve().parent
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
                    elif block.get("type") == "image":
                        print("Image found to be written")
                        f.write(f"[Image Caption]: {block['description']}\n")
        print(f"\n✅ Text extraction complete! Saved to '{output_file}'")

import sys
sys.stdout.reconfigure(encoding='utf-8')

def main():
    
    # pdf_path = "the_file.pdf"  # Kendi PDF dosyanızın yolunu belirtin
    pdf_path = "pdf_file.pdf"
    #pdf_path = "belge.pdf"
    #pdf_path = "file.pdf"
    #pdf_path = "image.pdf"
    if not os.path.exists(pdf_path):
        print(f"❌ Hata: {pdf_path} dosyası bulunamadı!")
        return
    
    print(f"📄 PDF dosyası bulundu: {pdf_path}")
    # Pipeline'ı başlat
    try:
        pipeline = UploadPipeline(
            pdf_path=pdf_path
        )
        
        print("🔍 PDF analiz ediliyor...")
        extracted_data = pipeline.run()
        
        print("\n✨ Analiz sonuçları:")
        print(f"- Toplam sayfa: {len(extracted_data['pages'])}")
        
        pipeline.save(extracted_data)
        
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")

    
"""    
    

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
"""
if __name__ == "__main__":
    main()