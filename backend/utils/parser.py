from PIL import Image
import io
import base64
import uuid
import os
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat, AnalyzeOutputOption
from backend.shared.constants import document_intelligence_client, IMAGES_PATH_STR, async_openai_client
from pathlib import Path

from backend.shared.logger import get_logger

logger = get_logger("PARSER")


async def describe_image(image_bytes):
        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = await async_openai_client.chat.completions.create(
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
        

async def AzureParser(file_path: str):
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

                description = await describe_image(img_data)

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

    return content


async def ImageParser(file_path: str):
    image_path = Path(file_path)
    if not image_path.exists():
        logger.warning(f"Görsel dosyası bulunamadı: {file_path}")
        return None

    with open(file_path, "rb") as f:
        image_bytes = f.read()

    image = Image.open(io.BytesIO(image_bytes))

    os.makedirs(IMAGES_PATH_STR, exist_ok=True)

    image_id = f"img_{uuid.uuid4().hex[:8]}"

    image_filename = f"{image_id}.png"
    saved_image_path = os.path.join(IMAGES_PATH_STR, image_filename)
    image.save(saved_image_path, format='PNG')

    description = await describe_image(image_bytes)

    content = f"\n\n**[Image ID:{image_id}]**\n\n{description}\n"

    logger.info(f"Image text extraction completed. Total length: {len(content)} characters")
    return content


def TxtParser(file_path: str):
    content_parts = []
    with open(file_path, "r", encoding="utf-8") as infile:
        for line in infile:
            if line.strip():
                content_parts.append(line)

    extracted_text = "".join(content_parts)
    return extracted_text