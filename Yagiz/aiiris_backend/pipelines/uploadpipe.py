from pathlib import Path
from PIL import Image
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import os, fitz, nltk, io
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from transformers import TapexTokenizer, BartForConditionalGeneration
import pandas as pd

class UploadPipeline:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.device = "cpu"
        self.azure_endpoint_doc_intel = "https://docaiiriswork.cognitiveservices.azure.com/"
        self.azure_key_doc_intel = "1Ab3Lpd2qh8sEtMCOZZLoW6QFqtBOVOYgwzcbo8I9BxBY9J3vtEcJQQJ99BEACYeBjFXJ3w3AAALACOG22i3"
        self.azure_endpoint_com_vis = "https://esracom.cognitiveservices.azure.com/"
        self.azure_key_com_vis = "1frCnTrE9FgLCRYEIN9AHpkQ8Mvj1v8fUbZrMtudo4GjYiaL1ZWJJQQJ99BEACYeBjFXJ3w3AAAFACOGU8g9"
        self.image_processor_url = "https://esracom.cognitiveservices.azure.com/" + "vision/v3.2/analyze"
        self.source_file = os.path.basename(pdf_path)

        if not self.azure_endpoint_doc_intel or not self.azure_key_doc_intel:
            raise ValueError(
                "Azure Document Intelligence credentials not provided. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY "
                "environment variables or pass them as parameters."
            )
        self.document_analysis_client = DocumentAnalysisClient( endpoint = self.azure_endpoint_doc_intel, credential = AzureKeyCredential(self.azure_key_doc_intel) )
    
    def run(self):
        # PDF dosyasını analiz et ve sonuçları al
        extracted_data = self.analyze_pdf_in_parts_and_collect_results(2)
        return extracted_data

    def describe_table_with_tapex(self, table_content, column_headers):
        # DataFrame oluştur
        df_data = {header: [] for header in column_headers}
        print("in describa table")
        for row in table_content:
            for i, cell in enumerate(row):
                header = column_headers[i]
                df_data[header].append(cell)

        df = pd.DataFrame(df_data)
        
        # Model ve tokenizer
        model_name = "microsoft/tapex-large"
        tokenizer = TapexTokenizer.from_pretrained(model_name)
        model = BartForConditionalGeneration.from_pretrained(model_name)
        
        query = "Summarize the table in detail."

        inputs = tokenizer(table=df, query=query, return_tensors="pt")
        outputs = model.generate(**inputs)
        explanation = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print("the explanation is: ", explanation)  
        return explanation
    
    def analyze_pdf_in_parts_and_collect_results(self, pages_per_part=2):
        # PDF dosyasını parçalara ayırır ve her parçayı analiz eder
        pdf = fitz.open(self.pdf_path)
        num_pages = len(pdf)
        save_dir = Path(__file__).resolve().parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        pdf_stem = Path(self.pdf_path).stem
        txt_output_path = save_dir / f"{pdf_stem}_txt.txt"

        with open(txt_output_path, 'w', encoding='utf-8') as dosya:
            for start_page in range(0, num_pages, pages_per_part):
                end_page = min(start_page + pages_per_part, num_pages)
                temp_pdf_path = save_dir / f"{pdf_stem}_part_{start_page+1}_to_{end_page}.pdf"
                temp_pdf = fitz.open()

                for page_num in range(start_page, end_page):
                    temp_pdf.insert_pdf(pdf, from_page=page_num, to_page=page_num)

                temp_pdf.save(temp_pdf_path)
                temp_pdf.close()

                with open(temp_pdf_path, "rb") as f:
                    poller = self.document_analysis_client.begin_analyze_document("prebuilt-layout", document=f)
                    result = poller.result()

                os.remove(temp_pdf_path)

                for page_num in range(start_page, end_page):
                    page = pdf.load_page(page_num)
                    dosya.write(f"\n------Page {page_num + 1}------\n\n")

                    table_boxes = []

                    # Tables
                    # Checks if there is a table in current page and takes the information in that table
                    page_tables = [t for t in result.tables if t.bounding_regions and t.bounding_regions[0].page_number == (page_num - start_page + 1)]
                    table_counter = 1
                    for table in page_tables:
                        dosya.write(f"\n[Table {table_counter}]\n")
                        table_content = []
                        header_row = []
                        max_col = max(cell.column_index for cell in table.cells)

                        # Header satırını dosyaya ve content'e yaz
                        for col_index in range(max_col + 1):
                            header_cell = next((cell for cell in table.cells if cell.row_index == 0 and cell.column_index == col_index), None)
                            content = header_cell.content if header_cell else f"Kolon {col_index+1}"
                            dosya.write(f"[0,{col_index}]: {content}\n")
                            header_row.append(content)
                            
                            if header_cell and header_cell.bounding_regions:
                                table_boxes.append(header_cell.bounding_regions[0].polygon)
                        
                        max_row = max(cell.row_index for cell in table.cells)

                        # Satır-sütun ve içerikleri txt'ye yaz + content listele
                        for row_index in range(1, max_row + 1):
                            row_content = []
                            for col_index in range(max_col + 1):
                                cell = next((cell for cell in table.cells if cell.row_index == row_index and cell.column_index == col_index), None)
                                content = cell.content if cell else ""
                                dosya.write(f"[{row_index},{col_index}]: {content}\n")
                                row_content.append(content)

                                if cell and cell.bounding_regions:
                                    table_boxes.append(cell.bounding_regions[0].polygon)
                            table_content.append(row_content)

                        # Tapex Large ile açıklama üret
                        table_description = self.describe_table_with_tapex(table_content, header_row)

                        dosya.write(f"\n[Table Explanation] : {table_description}\n\n")

                        table_counter += 1


                    if page_tables:
                        dosya.write("\n")

                    # Paragraphs
                    # Checks if there is a paragraph in current page and takes the information in that paragraph
                    page_paragraphs = [p for p in result.paragraphs if p.bounding_regions and p.bounding_regions[0].page_number == (page_num - start_page + 1)]
                    for paragraph in page_paragraphs:
                        
                        para_region = paragraph.bounding_regions[0].polygon
                        is_inside_table = any(self.check_overlap(para_region, box) for box in table_boxes)
                        
                        if is_inside_table:
                            continue
                        sentences = nltk.sent_tokenize(paragraph.content)
                        for sentence in sentences:
                            dosya.write(sentence + " ")
                        dosya.write("\n")

                    # Images
                    # Checks if there is an image in current page and appends the description of that image
                    images = page.get_images(full=True)
                    for img_index, img in enumerate(images):
                        try:
                            img_xref = img[0]
                            
                            img_bbox = page.get_image_bbox(img)
                            img_polygon = [
                                (img_bbox.x0, img_bbox.y0),
                                (img_bbox.x1, img_bbox.y0),
                                (img_bbox.x1, img_bbox.y1),
                                (img_bbox.x0, img_bbox.y1)
                            ]
                            is_inside_table = any(self.check_overlap(img_polygon, box) for box in table_boxes)
                            if is_inside_table:
                                print(f"Image {img_index + 1} is inside a table, skipping...")
                                continue

                            base_image = pdf.extract_image(img_xref)
                            image_bytes = base_image["image"]
                            description = self.describe_image(image_bytes)

                            dosya.write(f"\n[Image {img_index + 1}]\n")
                            dosya.write(f"Description: {description}\n")

                        except Exception as e:
                            print(f"Error processing image {img_index}: {e}")
                            continue

                print(f"{start_page+1}-{end_page}. sayfalar işlendi.")

        pdf.close()

    def describe_image(self, image_bytes):
        # Creates a description of the image using Azure Computer Vision
        try:
            image = Image.open(io.BytesIO(image_bytes))
            buf = io.BytesIO()
            image.save(buf, format='JPEG')
            jpeg_bytes = buf.getvalue()
            
            the_feature = [VisualFeatureTypes.description]

            computer_vision_client = ComputerVisionClient(
                self.azure_endpoint_com_vis,
                CognitiveServicesCredentials(self.azure_key_com_vis)
            )
            result = computer_vision_client.analyze_image_in_stream(
                image=io.BytesIO(jpeg_bytes),
                visual_features=the_feature,
                language="en"
            )
            if not result.description.captions:
                return "No description available"
            return result.description.captions[0].text
        except Exception as e:
            print(f"Error in image description: {e}")
            return "No description available"

    def check_overlap(self, box1, box2):
        """
        İki bounding box (polygon) arasında çakışma olup olmadığını kontrol eder.
        Her box, 4 noktalı [(x, y), ...] tuple listesi şeklinde
        """
        box1_x = [p[0] for p in box1]
        box1_y = [p[1] for p in box1]
        box2_x = [p[0] for p in box2]
        box2_y = [p[1] for p in box2]

        box1_left, box1_right = min(box1_x), max(box1_x)
        box1_top, box1_bottom = min(box1_y), max(box1_y)

        box2_left, box2_right = min(box2_x), max(box2_x)
        box2_top, box2_bottom = min(box2_y), max(box2_y)

        if box1_left > box2_right or box2_left > box1_right:
            return False
        if box1_top > box2_bottom or box2_top > box1_bottom:
            return False

        return True

def main():
    # pdf_path = "the_file.pdf"  # Kendi PDF dosyanızın yolunu belirtin
    pdf_path = "aiiris_backend/uploads/pdf_file.pdf"
    #pdf_path = "belge.pdf"
    #pdf_path = "file.pdf"
    #pdf_path = "image.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"X Hata: {pdf_path} dosyası bulunamadı!")
        return
    
    print(f" PDF dosyasi bulundu: {pdf_path}")
    # Pipeline'ı başlat
    try:
        pipeline = UploadPipeline( pdf_path=pdf_path )

        print(" PDF analiz ediliyor...")
        pipeline.run()

    except Exception as e:
        print(f"X Hata oluştu: {str(e)}")

if __name__ == "__main__":
    main()