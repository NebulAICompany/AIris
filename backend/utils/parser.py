from PIL import Image
import io
import base64
import uuid
import os
import hashlib
import json
from azure.ai.documentintelligence.models import (
    DocumentContentFormat,
    AnalyzeOutputOption,
)
from backend.shared.constants import (
    document_intelligence_client,
    IMAGES_PATH_STR,
    concurrent_client,
)
from pathlib import Path
from backend.shared.logger import get_logger
from backend.utils.table_clipper import (
    extract_table_images_from_pdf,
    create_table_regions_from_azure_result,
)

logger = get_logger("PARSER")

# JSON mapping file path
IMAGE_MAPPING_FILE = os.path.join(IMAGES_PATH_STR, "image_document_mapping.json")


def load_image_mapping() -> dict:
    """Load the image-to-document mapping from JSON file."""
    if os.path.exists(IMAGE_MAPPING_FILE):
        try:
            with open(IMAGE_MAPPING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading image mapping file: {e}")
    return {}


def save_image_mapping(mapping: dict):
    """Save the image-to-document mapping to JSON file."""
    try:
        os.makedirs(IMAGES_PATH_STR, exist_ok=True)
        with open(IMAGE_MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Error saving image mapping file: {e}")


def add_image_to_mapping(
    image_filename: str, document_name: str, image_type: str = "figure"
):
    """Add an image to the document mapping."""
    mapping = load_image_mapping()

    if image_filename not in mapping:
        mapping[image_filename] = {"document": document_name, "type": image_type}
        save_image_mapping(mapping)
        logger.info(f"Added {image_filename} to mapping for document {document_name}")


async def build_messages_for_image(image_bytes: bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    return [
        {
            "role": "system",
            "content": "You are an expert image analyst. Please provide a detailed and clear explanation of the given image in English.",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please describe this image in detail and provide an explanatory analysis in English.",
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
        model="gpt-4o",
        max_tokens=700,
        temperature=0.2,
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


async def AzureParser(file_path: str, photo_less_mode: bool = False):
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

    # Get document name for mapping
    document_name = os.path.splitext(os.path.basename(file_path))[0]

    # Ensure images directory exists
    os.makedirs(IMAGES_PATH_STR, exist_ok=True)

    logger.info(f"Processing document: {document_name}")

    if not photo_less_mode and result.figures:
        for figure in result.figures:
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

            # Generate consistent hash-based ID from image content
            content_hash = hashlib.sha256(img_base64.encode()).hexdigest()[:16]
            figure_id = f"fig_{content_hash}"

            image_filename = f"{figure_id}.png"
            image_path = os.path.join(IMAGES_PATH_STR, image_filename)

            # Only save the image if it doesn't already exist
            if not os.path.exists(image_path):
                with open(image_path, "wb") as w:
                    w.write(img_data)
                logger.info(f"Saved new image: {image_filename}")
                # Add to mapping
                add_image_to_mapping(image_filename, document_name, "figure")
            else:
                logger.info(f"Image already exists, skipping save: {image_filename}")

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
        logger.info("No figures found or photo_less mode is active.")

    # Extract table images if tables are found
    table_images = {}
    if result.tables:
        try:
            table_regions = create_table_regions_from_azure_result(result)
            if table_regions:
                # Save table images directly to images directory
                table_image_paths = extract_table_images_from_pdf(
                    pdf_path=file_path,
                    table_regions=table_regions,
                    output_dir=IMAGES_PATH_STR,
                    padding_inches=0.1,  # Add 0.1 inch padding around tables
                )

                # Create table images dictionary with IDs and descriptions
                for i, (region_info, table_image_path) in enumerate(
                    zip(table_regions, table_image_paths)
                ):
                    table_filename = os.path.basename(table_image_path)
                    table_id_region = region_info["table_id"]

                    # Add to mapping
                    add_image_to_mapping(table_filename, document_name, "table")
                    table_unique_id = table_filename.split(".")[0]
                    # Store table info
                    table_images[table_unique_id] = {
                        "filename": table_filename,
                        "table_id_region": table_id_region,
                        "page_number": region_info["page_number"],
                        "description": f"Table with {region_info['row_count']} rows and {region_info['column_count']} columns from page {region_info['page_number']}",
                    }

                logger.info(f"Extracted {len(table_image_paths)} table images")
        except Exception as e:
            logger.error(f"Error extracting table images: {str(e)}")

    content = result.content

    if not photo_less_mode:
        # Process figures
        for figure_id, data in figure_images.items():
            start = content.find("<figure>")
            if start != -1:
                end = content.find("</figure>", start) + 9
                caption = data["caption"] if data["caption"] else "no caption figure"
                desc = data.get("description", "No description")
                figure_md = f"\n\n**[{caption} ID:{figure_id}]**\n\n{desc}\n"
                content = content[:start] + figure_md + content[end:]
    else:
        # Remove entire figure blocks in photo-less mode
        while True:
            start = content.find("<figure>")
            if start == -1:
                break
            end = content.find("</figure>", start)
            if end == -1:
                content = content[:start]
                break
            content = content[:start] + content[end + len("</figure>") :]

    # Add table references to content (without removing table content)
    for table_unique_id, data in table_images.items():
        start = content.find("<table>")
        if start != -1:
            table_reference = (f"\n\n**[Table ID:{table_unique_id}]**\n\n{data['description']}\n")
            content = (
                content[:start]
                + table_reference
                + content[start + len(table_reference) :]
            )

    return content


async def ImageParser(file_path: str, photo_less_mode: bool = False):
    if not photo_less_mode:
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

        # Add to mapping
        document_name = os.path.splitext(os.path.basename(file_path))[0]
        add_image_to_mapping(image_filename, document_name, "image")

        descriptions = await describe_images([image_bytes])
        description = descriptions[0] if descriptions else "Açıklama alınamadı."

        content = f"\n\n**[Image ID:{image_id}]**\n\n{description}\n"
        return content
    else: 
        return "Photo-less mode enabled, image content omitted.\n"


async def TxtParser(file_path: str):
    with open(file_path, "r", encoding="utf-8") as infile:
        content = infile.read()

    return content
