import io
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import os, fitz, nltk, openai
from backend.pipelines.tools import describe_image, describe_table
from dotenv import load_dotenv
load_dotenv()
import nltk
from nltk.tokenize import sent_tokenize


# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt_tab")
except Exception as e:
    print(f"Error downloading NLTK data: {e}")
    nltk.download("punkt_tab", quiet=True)


class PdfParser:
    def __init__(self, pdf_path: str, txt_output_path: str):
        self.pdf_path = pdf_path
        self.azure_endpoint_doc_intel = os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
        )
        self.azure_key_doc_intel = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.txt_output_path = txt_output_path

        if not self.azure_endpoint_doc_intel or not self.azure_key_doc_intel:
            raise ValueError(
                "Azure Document Intelligence credentials not provided. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY "
                "environment variables or pass them as parameters."
            )
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.azure_endpoint_doc_intel,
            credential=AzureKeyCredential(self.azure_key_doc_intel)
        )

    def run(self):
        # PDF dosyasını analiz et ve sonuçları al
        extracted_data = self.process_pages_in_memory(2)
        return extracted_data

    def process_pages_in_memory(self, pages_per_part=2):
        pdf = fitz.open(self.pdf_path)
        num_pages = len(pdf)

        with open(self.txt_output_path, "w", encoding="utf-8") as dosya:
            for start_page in range(0, num_pages, pages_per_part):
                end_page = min(start_page + pages_per_part, num_pages)

                # Sayfaları bellekte yeni bir PDF olarak oluştur
                temp_pdf = fitz.open()
                for page_num in range(start_page, end_page):
                    temp_pdf.insert_pdf(pdf, from_page=page_num, to_page=page_num)

                # Bellekte PDF byte'larını al
                pdf_bytes = temp_pdf.tobytes()
                temp_pdf.close()

                # Azure Document Intelligence ile analiz et
                poller = self.document_analysis_client.begin_analyze_document(
                    "prebuilt-layout", document=io.BytesIO(pdf_bytes)
                )
                result = poller.result()

                # Sayfa sayfa işleme
                for local_page_num, page_num in enumerate(range(start_page, end_page)):
                    page = pdf.load_page(page_num)
                    dosya.write(f"\n------Page {page_num + 1}------\n\n")

                    occupied_boxes = []

                    # Görselleri işle
                    images = page.get_images(full=True)
                    for img_index, img in enumerate(images):
                        try:
                            img_xref = img[0]
                            img_bbox = page.get_image_bbox(img)
                            img_polygon = [
                                (img_bbox.x0, img_bbox.y0),
                                (img_bbox.x1, img_bbox.y0),
                                (img_bbox.x1, img_bbox.y1),
                                (img_bbox.x0, img_bbox.y1),
                            ]
                            base_image = pdf.extract_image(img_xref)
                            image_bytes = base_image["image"]
                            description = describe_image(image_bytes, client=self.client)
                            
                            updated_description = self.specify_sentence(description, "(Image)")

                            dosya.write(f"[Image {img_index + 1}]\n\n[Description] = {updated_description}\n---\n")
                            occupied_boxes.append(img_polygon)

                        except Exception as e:
                            print(f"Error processing image {img_index}: {e}")
                            continue

                    # Tabloları işle
                    page_tables = [t for t in result.tables if t.bounding_regions
                        and t.bounding_regions[0].page_number == (local_page_num + 1)]
                    
                    for table_counter, table in enumerate(page_tables):
                        table_regions = [region.polygon for region in table.bounding_regions]
                        
                        if any(self.check_overlap(region, occ) for region in table_regions for occ in occupied_boxes):
                            continue
                                    
                        dosya.write(f"\n[Table {table_counter + 1}]\n")
                        table_content = []
                        max_col = max(cell.column_index for cell in table.cells)
                        max_row = max(cell.row_index for cell in table.cells)

                        for row_index in range(max_row + 1):
                            for col_index in range(max_col + 1):
                                cell = next((cell for cell in table.cells if cell.row_index == row_index and cell.column_index == col_index), None,)
                                content = cell.content if cell else ""
                                if content:
                                    dosya.write(f"[{row_index},{col_index}]: {content}\n")
                                    table_content.append(content)

                        table_description = describe_table(table_content, client=self.client)
                        dosya.write(f"[Description] = {table_description}\n")
                        occupied_boxes.extend(table_regions)

                    if page_tables:
                        dosya.write("\n---\n")

                    # Paragrafları işle
                    page_paragraphs = [
                        p
                        for p in result.paragraphs
                        if p.bounding_regions
                        and p.bounding_regions[0].page_number == (local_page_num + 1)
                    ]
                    for paragraph in page_paragraphs:
                        para_region = paragraph.bounding_regions[0].polygon
                        if any(
                            self.check_overlap(para_region, box)
                            for box in occupied_boxes
                        ):
                            continue
                        sentences = nltk.sent_tokenize(paragraph.content)
                        for sentence in sentences:
                            dosya.write(sentence + " ")
                        dosya.write("\n")

                print(f"{start_page+1}-{end_page}. sayfalar bellekte işlendi.")

        pdf.close()
        print(f"Tüm PDF {self.txt_output_path} dosyasına kaydedildi.")

    def specify_sentence(self, text, word):
        """
        Adds a specified word to the end of each sentence using NLTK for sentence splitting.
        
        Args:
            text (str): Input text.
            word (str): Word to append at the end of each sentence.
            
        Returns:
            str: Modified text with the word added to each sentence.
        """
        sentences = sent_tokenize(text)
        modified_sentences = []
        
        for sentence in sentences:
            if sentence.strip():  # Skip empty sentences
                # Check if sentence ends with punctuation
                if sentence[-1] in {'.', '!', '?'}:
                    modified_sentence = sentence[:-1] + f" {word}" + sentence[-1]
                else:
                    modified_sentence = sentence + f" {word}"
                modified_sentences.append(modified_sentence)
        
        return ' '.join(modified_sentences)

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
