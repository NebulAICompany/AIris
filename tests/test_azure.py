from PIL import Image
import io
import base64
from nltk.tokenize import sent_tokenize
import uuid
import os
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat, AnalyzeOutputOption
from backend.shared.constants import document_intelligence_client, IMAGES_PATH_STR, openai_client
from pathlib import Path

from backend.shared.logger import get_logger

logger = get_logger("PARSER")


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
        if sentence.strip():
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


def AzureParser(file_path: str):
    with open(file_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            body=f,
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

                # Görseli açıklat
                description = describe_image(img_data)

                figure_images[figure_id] = {
                    'base64': img_base64,
                    'caption': figure_caption,
                    'image_path': image_path,
                    'description': description,
                }
    else:
        print("No figures found.")

    content = result.content

    for figure_id, figure_data in figure_images.items():
        figure_tag_start = content.find('<figure>')
        if figure_tag_start != -1:
            figure_tag_end = content.find('</figure>', figure_tag_start) + 9
            caption = figure_data["caption"] if figure_data["caption"] else "no caption figure"
            description = figure_data.get("description", "Açıklama alınamadı.")

            figure_markdown = f"\n\n**[{caption} ID:{figure_id}]**\n\n{description}\n"

            content = content[:figure_tag_start] + figure_markdown + content[
                figure_tag_end:]

    output_path = "C:/Users/ASUS/Desktop/Coding/CanProjects/AIris/backend/database/uploads/tcmb.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content


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

if __name__ == "__main__":
    sample_path = "C:/Users/ASUS/Desktop/Coding/CanProjects/AIris/backend/database/uploads/tcmb.pdf"
    AzureParser(sample_path)