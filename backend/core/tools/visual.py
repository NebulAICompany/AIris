from typing import List
from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, IMAGES_PATH_STR
import base64
import os
from langchain_core.tools import tool
from backend.core.prompts import redescribe_image_prompt

logger = get_logger("VISUAL")

IMAGE_DATA = []


def get_image_datas():
    return IMAGE_DATA


def set_image_datas(data):
    global IMAGE_DATA
    if isinstance(data, list):
        IMAGE_DATA.extend(data)
    else:
        IMAGE_DATA.append(data)


def clear_image_datas():
    global IMAGE_DATA
    IMAGE_DATA.clear()


@tool
def image_visualizer(image_ids: List[str]) -> str:
    """
    Load and display images to the frontend based on image IDs found in RAG context.

    This function should be called when the agent determines that displaying actual images
    would enhance user understanding, based on image descriptions and references found in
    the local context (patterns like "ID:img_12345678", "ID:fig_87654321", or "ID:table_12345678").
    IMPORTANT: Do not call this tool multiple times for the same image IDs. Each image will only be loaded once per query.

    Args:
        image_ids: List of complete image identifiers including prefixes
                  Examples: ["img_12345678", "fig_87654321", "table_12345678"] for corresponding image files

    Returns:
        str: Success message indicating how many images were loaded successfully
    """

    logger.info(f"Loading images... {image_ids}")
    images_data = []

    for img_id in image_ids:
        logger.info(f"Checking for image: {img_id}")
        image_file_path = None
        found = False

        for ext in [".jpg", ".png"]:
            logger.info(f"Checking for image with extension: {ext}")
            image_file_path = f"{IMAGES_PATH_STR}/{img_id}{ext}"
            logger.info(f"Loading image from path: {image_file_path}")

            if os.path.exists(image_file_path):
                logger.info(f"Image found: {image_file_path}")
                try:
                    with open(image_file_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode("utf-8")
                        logger.info(f"Image data loaded successfully: {img_id}{ext}")
                        images_data.append(
                            {
                                "filename": f"{img_id}{ext}",
                                "data": img_data,
                                "reference": img_id,
                                "type": f"image/{ext[1:]}",
                            }
                        )
                    found = True
                    break
                except Exception as e:
                    logger.error(f"   ❌ Error loading image {img_id}{ext}: {e}")

        if not found:
            logger.warning(f"Image not found for ID: {img_id}")

    set_image_datas(images_data)

    return "Successfully loaded images into attachments. Do not add into answer, it is already in attachments."


@tool
def describe_image_content(image_id: str, user_query: str) -> str:
    """
    Analyze an image based on a user query using OpenAI's vision capabilities.

    This tool should be used when you need to understand the content of an image
    in relation to a specific user question. It will provide detailed analysis
    focused on the query context.

    Args:
        image_id: Image identifier (e.g., "img_12345678", "fig_87654321", "table_12345678")
        user_query: The user's question or query about the image

    Returns:
        str: Detailed analysis of the image content relevant to the query
    """

    try:
        full_path = None
        found = False

        # Check if image_id already has an extension
        if os.path.splitext(image_id)[1]:
            # Has extension, try direct path
            full_path = f"{IMAGES_PATH_STR}/{image_id}"
            if os.path.exists(full_path):
                found = True
        else:
            # No extension, try common extensions
            for ext in [".jpg", ".jpeg", ".png"]:
                full_path = f"{IMAGES_PATH_STR}/{image_id}{ext}"
                if os.path.exists(full_path):
                    found = True
                    break

        if not found or not full_path:
            return f"Error: Image file not found for '{image_id}'. Tried paths with extensions: .jpg, .jpeg, .png"

        # Read and encode image
        with open(full_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        # Get file extension for MIME type with better support
        file_ext = os.path.splitext(full_path)[1].lower()
        mime_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        mime_type = mime_type_map.get(file_ext, "image/png")  # Default fallback

        # Prepare messages with the enhanced prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{redescribe_image_prompt}\n\nUser Query: {user_query}",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ]

        response = openai_client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            max_completion_tokens=1500,
            temperature=0.1,
        )

        # Validate response
        if not response.choices or not response.choices[0].message.content:
            return "Error: No response received from OpenAI Vision API"

        analysis_result = response.choices[0].message.content
        logger.info(f"Successfully analyzed image: {image_id}")
        return f"Image Analysis Results:\n\n{analysis_result}"

    except Exception as e:
        error_msg = f"Error analyzing image {image_id}: {str(e)}"
        logger.error(error_msg)
        return error_msg
