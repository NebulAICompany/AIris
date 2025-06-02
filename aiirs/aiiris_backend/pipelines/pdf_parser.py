from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import os, fitz, nltk, base64, openai
from pathlib import Path

class PdfParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.azure_endpoint_doc_intel = "https://docaiiriswork.cognitiveservices.azure.com/"
        self.azure_key_doc_intel = "1Ab3Lpd2qh8sEtMCOZZLoW6QFqtBOVOYgwzcbo8I9BxBY9J3vtEcJQQJ99BEACYeBjFXJ3w3AAALACOG22i3"
        self.client = openai.OpenAI(api_key="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")

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

    def analyze_pdf_in_parts_and_collect_results(self, pages_per_part=2):
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

                    # Bounding boxes trackers
                    occupied_boxes = []

                    ## 1️⃣ Images
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
                            base_image = pdf.extract_image(img_xref)
                            image_bytes = base_image["image"]
                            description = self.describe_image(image_bytes)

                            dosya.write(f"[Image {img_index + 1}]\n\n[Description] = {description}\n---\n")
                            occupied_boxes.append(img_polygon)

                        except Exception as e:
                            print(f"Error processing image {img_index}: {e}")
                            continue

                    ## 2️⃣ Tables
                    page_tables = [t for t in result.tables if t.bounding_regions and t.bounding_regions[0].page_number == (page_num - start_page + 1)]
                    for table_counter, table in enumerate(page_tables):
                        # Check if this table overlaps any occupied area (image)
                        table_regions = [region.polygon for region in table.bounding_regions]
                        if any(self.check_overlap(region, occ) for region in table_regions for occ in occupied_boxes):
                            continue

                        dosya.write(f"\n[Table {table_counter + 1}]\n")
                        table_content = []
                        
                        max_col = max(cell.column_index for cell in table.cells)
                        max_row = max(cell.row_index for cell in table.cells)
                        
                        for row_index in range(max_row + 1):
                            for col_index in range(max_col + 1):
                                cell = next((cell for cell in table.cells if cell.row_index == row_index and cell.column_index == col_index), None)
                                content = cell.content if cell else ""
                                if not content == "":
                                    dosya.write(f"[{row_index},{col_index}]: {content}\n")
                                    table_content.append(content)

                        
                        table_description = self.describe_table(table_content)
                        dosya.write(f"[Description] = {table_description} \n")
                        # Append all table regions to occupied_boxes
                        occupied_boxes.extend(table_regions)

                    if page_tables:
                        dosya.write("\n---\n")

                    ## 3️⃣ Paragraphs
                    page_paragraphs = [p for p in result.paragraphs if p.bounding_regions and p.bounding_regions[0].page_number == (page_num - start_page + 1)]
                    for paragraph in page_paragraphs:
                        para_region = paragraph.bounding_regions[0].polygon
                        if any(self.check_overlap(para_region, box) for box in occupied_boxes):
                            continue
                        sentences = nltk.sent_tokenize(paragraph.content)
                        for sentence in sentences:
                            dosya.write(sentence + " ")
                        dosya.write("\n")

                print(f"{start_page+1}-{end_page}. sayfalar işlendi.")

        pdf.close()


    def describe_image(self, image_bytes):
        try:
            #client = openai.OpenAI(api_key="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")

            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sen uzman bir görüntü analizcisisin. Gönderilen görseli grafik mi fotoğraf mı olduğunu belirle. Fotoğrafsa neyi gösterdiğini kısaca söyle, grafikse oldukça detaylı biçimde finans konseptiyle açıkla."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Lütfen bu görseli inceleyip önce türünü belirt, grafikse türünü ve detaylı açıklamasını yap."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=700
            )

            description = response.choices[0].message.content
            return description

        except Exception as e:
            print(f"Error in GPT image description: {e}")
            return "Açıklama alınamadı."

    def describe_table(self, table_content):
        try:
            table_text = "\n".join([" | ".join(row) for row in table_content])
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sen uzman bir veri analistisin. Aşağıda bir tablo verilecek. Tabloyu inceleyip detaylıca analiz et, öne çıkan değerleri ve yorumlarını yaz."},
                    {"role": "user", "content": f"Tablo:\n{table_text}\n\nLütfen bu tabloyu detaylı yorumla:"}
                ],
                max_tokens=800
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"Error in GPT table description: {e}")
            return "Tablo açıklaması alınamadı."
        
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