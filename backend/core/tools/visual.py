from typing import List, Dict
from backend.shared.logger import get_logger
import base64
import os
from agents import function_tool

logger = get_logger("VISUAL")

all_image_data = []

def get_image_datas():
    return all_image_data

def set_image_datas(data):
    global all_image_data
    all_image_data = data

@function_tool
def image_visualizer(image_ids: List[str]) -> str:
    """
    Load and display images to the frontend based on image IDs found in RAG context.

    This function should be called when the agent determines that displaying actual images
    would enhance user understanding, based on image descriptions and references found in
    the local context (patterns like "ID:img_12345678" or "ID:fig_87654321").

    Args:
        image_ids: List of complete image identifiers including prefixes
                  Examples: ["img_12345678", "fig_87654321"] for corresponding image files

    Returns:
        str: Success message indicating how many images were loaded successfully
    """

    logger.info(f"Loading images... {image_ids}]")
    images_data = []

    for img_id in image_ids:
        logger.info(f"Checking for image: {img_id}")
        for ext in ['.jpg', '.png']:
            logger.info(f"Checking for image with extension: {ext}")
            image_file_path = f"backend/database/uploads/images/{img_id}{ext}"
            logger.info(f"Loading image from path: {image_file_path}")

        if os.path.exists(image_file_path):
            logger.info(f"Image found: {image_file_path}")
            try:
                with open(image_file_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    logger.info(f"Image data loaded successfully: {img_id}{ext}")
                    images_data.append({
                        "filename": f"{img_id}{ext}",
                        "data": img_data,
                        "reference": img_id,
                        "type": f"image/{ext[1:]}"
                    })
                break
            except Exception as e:
                logger.error(f"   ❌ Error loading image {img_id}{ext}: {e}")

    set_image_datas(images_data)

    return "images loaded successfully"