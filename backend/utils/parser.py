from PIL import Image
import io
import base64
import uuid
import os
import hashlib
import json
import re
import pandas as pd
from pathlib import Path
from azure.ai.documentintelligence.models import (
    DocumentContentFormat,
    AnalyzeOutputOption,
)
from backend.shared.constants import (
    document_intelligence_client,
    IMAGES_PATH_STR,
    co,
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


def image_to_base64_data_url(image_bytes: bytes, image_format: str = "png") -> str:
    """Convert image bytes to base64 data URL format for Cohere API"""
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/{image_format};base64,{base64_image}"


def embed_image_with_caption(image_bytes: bytes, caption: str, figure_id: str) -> list:
    """
    Embed an image with its caption using Cohere embed-v4.0 multimodal API.

    Args:
        image_bytes: Image data as bytes
        caption: Caption text from Azure Document Intelligence
        figure_id: Unique figure ID

    Returns:
        Embedding vector as list, or None on failure
    """
    try:
        # Convert image to base64 data URL
        base64_data_url = image_to_base64_data_url(image_bytes, "png")

        # Always include figure_id, and include caption if it exists
        caption_text = f"{caption} {figure_id}" if caption else f"Figure {figure_id}"
        multimodal_input = {
            "content": [
                {"type": "image_url", "image_url": {"url": base64_data_url}},
                {"type": "text", "text": caption_text},
            ]
        }

        # Embed using Cohere
        response = co.embed(
            inputs=[multimodal_input],
            model="embed-v4.0",
            input_type="search_document",
            output_dimension=1536,
            embedding_types=["float"],
        )

        return response.embeddings.float[0]
    except Exception as e:
        logger.error(f"Error embedding image {figure_id}: {e}")
        return None


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
    # Get document name for mapping
    document_name = os.path.splitext(os.path.basename(file_path))[0]

    # Ensure images directory exists
    os.makedirs(IMAGES_PATH_STR, exist_ok=True)

    logger.info(f"Processing document: {document_name}")

    if not photo_less_mode and result.figures:
        logger.info(f"Extracting {len(result.figures)} figure(s)...")
        for figure in result.figures:
            caption = figure.caption.content if figure.caption else ""
            if not figure.id:
                continue
            figure_page_number = None
            if figure.bounding_regions:
                figure_page_number = figure.bounding_regions[0].page_number

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
                "image_bytes": img_data,
                "page_number": figure_page_number,
            }
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

    if result.pages:
        page_spans = [
            (page.spans[0].offset, page.page_number)
            for page in result.pages
            if page.spans
        ]
        for offset, page_num in sorted(page_spans, key=lambda x: x[0], reverse=True):
            marker = f"<!-- PAGE_BREAK:{page_num} -->"
            content = content[:offset] + marker + content[offset:]

    content = re.sub(r"<!-- Page(?:Header|Footer|Number|Break)[^>]*-->", "", content)
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
            table_reference = f"\n\n**[Table ID:{table_unique_id}]**\n\n"
            content = (
                content[:start]
                + table_reference
                + "<table_processed>"
                + content[start + len("<table>"):]
            )
    content = content.replace("<table_processed>", "<table>")

    return content, figure_images


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

        caption = f"Image from {document_name}"
        content = f"\n\n**[Image ID:{image_id}]**\n\n{caption}\n"
        return content
    else:
        return "Photo-less mode enabled, image content omitted.\n"


async def TxtParser(file_path: str):
    with open(file_path, "r", encoding="utf-8") as infile:
        content = infile.read()

    return content


async def ExcelParser(file_path: str) -> str:
    df = pd.read_excel(file_path, sheet_name=None)
    table_name = Path(file_path).stem
    contents = []
    for sheet_name, sheet_data in df.items():

        sheet_data.fillna("", inplace=True)
        contents.append(
            f"**[Table Name: {table_name}]**\n**[Sheet Name:{sheet_name}]**\n\n{sheet_data.to_markdown()}\n"
        )

    return "\n====SHEET SEPARATOR====\n".join(contents)
