from PIL import Image
import io
import base64
import uuid
import os
from azure.ai.documentintelligence.models import (
    AnalyzeResult,
    DocumentContentFormat,
    AnalyzeOutputOption,
)
from backend.shared.constants import (
    document_intelligence_client,
    IMAGES_PATH_STR,
    concurrent_client,
    OPENAI_MODEL,
)
from pathlib import Path

from backend.shared.logger import get_logger

logger = get_logger("PARSER")


async def build_messages_for_image(image_bytes: bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    return [
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
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                },
            ],
        },
    ]


async def describe_images(image_bytes_list: list[bytes]) -> list[str]:
    messages_list = []
    for img in image_bytes_list:
        messages = await build_messages_for_image(img)
        messages_list.append(messages)

    responses = await concurrent_client.create_many(
        messages_list=messages_list,
        model=OPENAI_MODEL,
        max_tokens=700,
    )

    descriptions = []
    for resp in responses:
        if isinstance(resp, Exception):
            descriptions.append("Açıklama alınamadı.")
        else:
            content = getattr(resp, "content", None)
            if not content:
                content = resp.choices[0].message.content
            descriptions.append(content)
    return descriptions


async def AzureParser(file_path: str):
    with open(file_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            body=f,
            output_content_format=DocumentContentFormat.MARKDOWN,
            output=[AnalyzeOutputOption.FIGURES],
        )
    result = poller.result()
    operation_id = poller.details["operation_id"]

    figure_images = {}
    image_bytes_batch = []
    figure_order = []

    os.makedirs(IMAGES_PATH_STR, exist_ok=True)

    if result.figures:
        for figure in result.figures:
            figure_id = f"fig_{uuid.uuid4().hex[:8]}"
            caption = figure.caption.content if figure.caption else ""
            if not figure.id:
                continue

            response = document_intelligence_client.get_analyze_result_figure(
                model_id=result.model_id,
                result_id=operation_id,
                figure_id=figure.id,
            )
            img_data = b"".join(response)
            img_base64 = base64.b64encode(img_data).decode()

            image_filename = f"{figure_id}.png"
            image_path = os.path.join(IMAGES_PATH_STR, image_filename)
            with open(image_path, "wb") as w:
                w.write(img_data)

            figure_images[figure_id] = {
                "base64": img_base64,
                "caption": caption,
                "image_path": image_path,
                "description": None,
            }
            image_bytes_batch.append(img_data)
            figure_order.append(figure_id)

        # Paralel ve rate-limit güvenli açıklama
        if image_bytes_batch:
            descriptions = await describe_images(image_bytes_batch)
            for fid, desc in zip(figure_order, descriptions):
                figure_images[fid]["description"] = desc
    else:
        logger.info("No figures found.")

    content = result.content
    for figure_id, data in figure_images.items():
        start = content.find("<figure>")
        if start != -1:
            end = content.find("</figure>", start) + 9
            caption = data["caption"] if data["caption"] else "no caption figure"
            desc = data.get("description", "Açıklama alınamadı.")
            figure_md = f"\n\n**[{caption} ID:{figure_id}]**\n\n{desc}\n"
            content = content[:start] + figure_md + content[end:]

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
    image.save(saved_image_path, format="PNG")

    descriptions = await describe_images([image_bytes])
    description = descriptions[0] if descriptions else "Açıklama alınamadı."

    content = f"\n\n**[Image ID:{image_id}]**\n\n{description}\n"

    logger.info(
        f"Image text extraction completed. Total length: {len(content)} characters"
    )
    return content


async def TxtParser(file_path: str):
    with open(file_path, "r", encoding="utf-8") as infile:
        content = infile.read()

    return content
