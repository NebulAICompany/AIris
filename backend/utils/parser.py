import pythoncom
from docx2pdf import convert
from PIL import Image
import io
import base64
from nltk.tokenize import sent_tokenize
import openpyxl
import fitz
import nltk
import uuid
import os
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat, AnalyzeDocumentRequest, AnalyzeOutputOption
from backend.shared.constants import document_analysis_client, document_intelligence_client, IMAGES_PATH, IMAGES_PATH_STR, openai_client
from pathlib import Path

from backend.shared.logger import get_logger

logger = get_logger("PARSER")


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
            logger.error(f"Error in GPT image description: {e}")
            return "Açıklama alınamadı."
        

def PdfParser(file_path: str):
    pdf = fitz.open(file_path)
    pdf_bytes = pdf.tobytes()

    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout",
        AnalyzeDocumentRequest(bytes_source=pdf_bytes),
        output_content_format=DocumentContentFormat.MARKDOWN,
        output=[AnalyzeOutputOption.FIGURES]
    )

    result: AnalyzeResult = poller.result()
    operation_id = poller.details["operation_id"]

    figure_images = {}
    os.makedirs(IMAGES_PATH_STR, exist_ok=True)

    if result.figures:
        for figure_idx, figure in enumerate(result.figures):
            figure_id = f"fig_{uuid.uuid4().hex[:8]}"
            figure_caption = figure.caption.content if figure.caption else ""

            if figure.id:
                response = document_intelligence_client.get_analyze_result_figure(
                    model_id=result.model_id,
                    result_id=operation_id,
                    figure_id=figure.id
                )

                img_data = b"".join(response)

                img_base64 = base64.b64encode(img_data).decode()

                image_filename = f"{figure_id}.png"
                image_path = os.path.join(IMAGES_PATH_STR, image_filename)

                with open(image_path, "wb") as writer:
                    writer.write(img_data)

                figure_images[figure_id] = {
                    'base64': img_base64,
                    'caption': figure_caption,
                    'image_path': image_path,
                }
    else:
        print("No figures found.")

    markdown_content = result.content

    for figure_id, figure_data in figure_images.items():
        figure_tag_start = markdown_content.find('<figure>')
        if figure_tag_start != -1:
            figure_tag_end = markdown_content.find('</figure>', figure_tag_start) + 9

            figure_markdown = f"\n\n[{figure_caption} ** ID:`{figure_id}]`**"

            markdown_content = markdown_content[:figure_tag_start] + figure_markdown + markdown_content[
                figure_tag_end:]

    output_path = "C:/Users/ASUS/Desktop/Coding/CanProjects/AIris/backend/database/uploads/tcmb.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    pdf.close()

    return markdown_content


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
        logger.info(f"Excel text extraction completed. Total length: {len(extracted_text)} characters")
        return extracted_text

def ImageParser(file_path: str):
    image_path = Path(file_path)
    if not image_path.exists():
        logger.warning(f"Görsel dosyası bulunamadı: {file_path}")
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
    
    logger.info(f"Image text extraction completed. Total length: {len(content)} characters")
    return content


def TxtParser(file_path: str):
        content_parts = []
        with open(file_path, "r", encoding="utf-8") as infile:
            for line in infile:
                if line.strip():  # satır boş değilse
                    content_parts.append(line)

        extracted_text = "".join(content_parts)
        logger.info(f"TXT text extraction completed. Total length: {len(extracted_text)} characters")
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
            logger.warning(f"PDF dosyası bulunamadı: {file_path}")
            return None
        else:
            # PDF'i parse et ve text'i al
            extracted_text = PdfParser(file_path)

            logger.info("DOCX to PDF ve text extraction işlemi tamamlandı.")
            
            # Geçici PDF dosyasını sil
            try:
                Path(file_path).unlink()
            except Exception as e:
                logger.error(f"{file_path} silinemedi: {e}")
            
            return extracted_text

