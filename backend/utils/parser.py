import pythoncom
from docx2pdf import convert
from pathlib import Path
from PIL import Image
import io
import base64
from nltk.tokenize import sent_tokenize
import openpyxl
import fitz
import nltk
from backend.shared.constants import document_analysis_client, IMAGES_PATH, openai_client


# NOTE: Helper functions for specifications of information (Describe image and add configurations to sentences with relevant information)

def specify_sentence(text, word):
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


def describe_image(image_bytes):
        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen uzman bir görüntü analizcisisin. Gönderilen görseli detaylı ve anlaşılır bir şekilde Türkçe olarak açıkla.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Lütfen bu görseli detaylı ve açıklayıcı bir şekilde Türkçe olarak açıkla.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
                max_tokens=700,
            )
            description = response.choices[0].message.content
            return description

        except Exception as e:
            print(f"Error in GPT image description: {e}")
            return "Açıklama alınamadı."
        

# NOTE: Parser after this line


def PdfParser(file_path: str):
    pages_per_part = 2
    dpi = 300
    min_area= 100000
    pdf = fitz.open(file_path)
    num_pages = len(pdf)

    images_dir = Path(IMAGES_PATH)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Text content'i bellekte biriktir
    content_parts = []
    
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
            poller = document_analysis_client.begin_analyze_document(
                "prebuilt-layout", document=io.BytesIO(pdf_bytes)
            )
            result = poller.result()

            # Sayfa sayfa işleme
            for local_page_num, page_num in enumerate(range(start_page, end_page)):
                page = pdf.load_page(page_num)
                content_parts.append(f"\n------Page {page_num + 1}------\n\n")
                
                occupied_boxes = []
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                page_image = Image.open(io.BytesIO(pix.tobytes("png")))

                # Görselleri işle
                drawings = page.get_drawings()
                images = page.get_images(full=True)
                candidate_rects = []

                # Görseller
                for img in images:
                    xref = img[0]
                    for rect in page.get_image_rects(xref):
                        x0, y0, x1, y1 = [int(c * dpi / 72) for c in rect]
                        candidate_rects.append((x0, y0, x1, y1))

                # Çizimler
                for drawing in drawings:
                    if 'rect' in drawing:
                        rect = drawing['rect']
                        x0, y0, x1, y1 = [int(c * dpi / 72) for c in rect]
                        candidate_rects.append((x0, y0, x1, y1))

                merged_rects = []
                for rect in sorted(candidate_rects, key=lambda r: -(r[2]-r[0])*(r[3]-r[1])):  # Büyükten küçüğe
                    merged = False
                    for i, existing in enumerate(merged_rects):
                        if rects_overlap(rect, existing):
                            merged_rects[i] = merge_rects(rect, existing)
                            merged = True
                            break
                    if not merged:
                        merged_rects.append(rect)

                # Kırp ve kaydet (önce alan kontrolü, sonra genişletme)
                for idx, rect in enumerate(merged_rects):
                    x0, y0, x1, y1 = [int(v) for v in rect]
                    area = (x1 - x0) * (y1 - y0)
                    if area > min_area and x1 > x0 and y1 > y0:
                        # Genişletmeyi sadece kaydedilecek rect'lere uygula
                        expanded = expand_rect(
                            rect,
                            expand_top=80,
                            expand_bottom=100,
                            expand_left=40,
                            expand_right=40,
                            max_width=page_image.width,
                            max_height=page_image.height
                        )
                        x0, y0, x1, y1 = [int(v) for v in expanded]
                        cropped = page_image.crop((x0, y0, x1, y1))
                        pdf_name = Path(file_path).stem  # Dosya adını uzantısız al
                        filename = f"{images_dir}/{pdf_name}_page_{page_num + 1}_{idx + 1}.png"
                        cropped.save(filename)

                        # Image reference için sadece dosya adını kullan (path ve uzantı olmadan)
                        image_reference = f"{pdf_name}_page_{page_num + 1}_{idx + 1}"

                        # PIL Image'ı bytes'a çevir
                        img_byte_arr = io.BytesIO()
                        cropped.save(img_byte_arr, format='PNG')
                        img_bytes = img_byte_arr.getvalue()

                        description = describe_image(img_bytes)
                        updated_description = specify_sentence(description, f"((Image):{image_reference})")

                        content_parts.append(f"{updated_description}\n---\n")
                        occupied_boxes.append(expanded)
                pix = None  # Bellek temizleme

                # Tabloları işle
                page_tables = [t for t in result.tables if t.bounding_regions
                    and t.bounding_regions[0].page_number == (local_page_num + 1)]
                
                for table_counter, table in enumerate(page_tables):
                    table_regions = [region.polygon for region in table.bounding_regions]

                    if any(rects_overlap(region, occ) for region in table_regions for occ in occupied_boxes):
                        continue
                                
                    content_parts.append(f"\n[Table {table_counter + 1}]\n")
                    max_col = max(cell.column_index for cell in table.cells)
                    max_row = max(cell.row_index for cell in table.cells)

                    for row_index in range(max_row + 1):
                        for col_index in range(max_col + 1):
                            cell = next((cell for cell in table.cells if cell.row_index == row_index and cell.column_index == col_index), None,)
                            content = cell.content if cell else ""
                            if content:
                                content_parts.append(f"[{row_index},{col_index}]: {content}\n")

                    occupied_boxes.extend(table_regions)

                if page_tables:
                    content_parts.append("\n---\n")

                # Paragrafları işle
                page_paragraphs = [
                    p for p in result.paragraphs if p.bounding_regions and p.bounding_regions[0].page_number == (local_page_num + 1)]
                
                for paragraph in page_paragraphs:
                    para_region = paragraph.bounding_regions[0].polygon
                    if any(rects_overlap(para_region, box) for box in occupied_boxes):
                        continue
                    
                    sentences = nltk.sent_tokenize(paragraph.content)
                    for sentence in sentences:
                        content_parts.append(sentence + " ")
                    content_parts.append("\n")

            print(f"{start_page+1}-{end_page}. sayfalar bellekte işlendi.")

    pdf.close()
    
    # Tüm content_parts'ı birleştir ve return et
    extracted_text = "".join(content_parts)
    print(f"PDF text extraction completed. Total length: {len(extracted_text)} characters")
    
    return extracted_text


def rects_overlap(r1, r2):
    r1  = convert_to_rect(r1)
    r2  = convert_to_rect(r2)
    
    if not r1 or not r2:
        return False
    
    threshold = 0.3
    x0 = max(r1[0], r2[0])
    y0 = max(r1[1], r2[1])
    x1 = min(r1[2], r2[2])
    y1 = min(r1[3], r2[3])
    if x1 <= x0 or y1 <= y0:
        return False
    intersection = (x1 - x0) * (y1 - y0)
    area1 = (r1[2] - r1[0]) * (r1[3] - r1[1])
    area2 = (r2[2] - r2[0]) * (r2[3] - r2[1])
    return intersection / min(area1, area2) > threshold

def merge_rects(r1, r2):
    return (min(r1[0], r2[0]), min(r1[1], r2[1]),
            max(r1[2], r2[2]), max(r1[3], r2[3]))

def expand_rect(rect, expand_top=0, expand_bottom=30, expand_left=0, expand_right=0, max_width=None, max_height=None):
    x0, y0, x1, y1 = rect
    x0 -= expand_left
    y0 -= expand_top
    x1 += expand_right
    y1 += expand_bottom
    if max_width is not None:
        x0 = max(0, x0)
        x1 = min(max_width, x1)
    if max_height is not None:
        y0 = max(0, y0)
        y1 = min(max_height, y1)
    return (x0, y0, x1, y1)

def convert_to_rect(box):
    """
    Box tipi:
    - Eğer (x0, y0, x1, y1) formatındaysa direkt döner.
    - Eğer Azure polygon formatındaysa, onu bbox'a çevirir.
    """
    if isinstance(box, tuple) and len(box) == 4:
        return box
    elif isinstance(box, list) and all(hasattr(p, "x") and hasattr(p, "y") for p in box):
        xs = [p.x for p in box]
        ys = [p.y for p in box]
        return (min(xs), min(ys), max(xs), max(ys))
    elif isinstance(box, list) and all(isinstance(p, tuple) and len(p) == 2 for p in box):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        return (min(xs), min(ys), max(xs), max(ys))
    else:
        raise ValueError(f"Geçersiz bbox formatı: {box}")

def ExcelParser(file_path: str):
        wb_obj = openpyxl.load_workbook(file_path)
        
        content_parts = []
        for sheet in wb_obj.sheetnames:
            content_parts.append(f"--- Sheet: {sheet} ---\n")
            worksheet = wb_obj[sheet]

            # Eğer bu bir normal worksheet ise
            if isinstance(worksheet, openpyxl.worksheet.worksheet.Worksheet):
                for row in worksheet.iter_rows():
                    for cell in row:
                        value = cell.value if cell.value is not None else ""
                        if not value == "":
                            content_parts.append(f"[{cell.row}, {cell.column}] = {value}\n")


        # Tüm content_parts'ı birleştir ve return et
        extracted_text = "".join(content_parts)
        print(f"Excel text extraction completed. Total length: {len(extracted_text)} characters")
        return extracted_text

def ImageParser(file_path: str):
    image_path = Path(file_path)
    if not image_path.exists():
        print(f"Görsel dosyası bulunamadı: {file_path}")
        return None

    with open(file_path, "rb") as f:
        image_bytes = f.read()

    # Görseli aç (PIL kullanarak)
    image = Image.open(io.BytesIO(image_bytes))

    # images/ klasörü oluşturulmamışsa oluştur
    images_dir = Path(__file__).parent.parent / "images"
    images_dir.mkdir(exist_ok=True)

    # Image reference için sadece dosya adını kullan (uzantısız)
    image_reference = Path(file_path).stem
    
    # Görseli kaydet
    saved_image_path = images_dir / f"{image_reference}.png"
    image.save(saved_image_path, format='PNG')

    # Açıklamayı al
    description = describe_image(image_bytes)
    updated_description = specify_sentence(description, f"((Image):{image_reference})")

    # Text content'i hazırla
    content = f"Açıklama:\n{updated_description}\n"
    
    print(f"Image text extraction completed. Total length: {len(content)} characters")
    return content


def TxtParser(file_path: str):
        content_parts = []
        with open(file_path, "r", encoding="utf-8") as infile:
            for line in infile:
                if line.strip():  # satır boş değilse
                    content_parts.append(line)

        extracted_text = "".join(content_parts)
        print(f"TXT text extraction completed. Total length: {len(extracted_text)} characters")
        return extracted_text


def DocxParser(file_path: str):
        # Initialize COM at the beginning
        pythoncom.CoInitialize()

        from backend.shared.constants import UPLOADS_PATH
        output_dir = Path(UPLOADS_PATH)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_pdf = output_dir / (Path(file_path).stem + ".pdf")
        convert(file_path, str(output_pdf))

        file_path = str(output_pdf)
        if not Path(file_path).exists():
            print(f"PDF dosyası bulunamadı: {file_path}")
            return None
        else:
            # PDF'i parse et ve text'i al
            extracted_text = PdfParser(file_path)

            print("DOCX to PDF ve text extraction işlemi tamamlandı.")
            
            # Geçici PDF dosyasını sil
            try:
                Path(file_path).unlink()
            except Exception as e:
                print(f"{file_path} silinemedi: {e}")
            
            return extracted_text