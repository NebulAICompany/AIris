from typing import List
from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, IMAGES_PATH_STR
import base64
import os
from backend.core.prompts import describe_image_prompt
from langchain_core.tools import tool

logger = get_logger("VISUAL")

IMAGE_DATA = {}


def get_image_datas():
    return list(IMAGE_DATA.values())


def set_image_datas(data):
    global IMAGE_DATA
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                unique_id = item.get("reference")
                if unique_id:
                    IMAGE_DATA[unique_id] = item
    elif isinstance(data, dict):
        unique_id = data.get("reference")
        if unique_id:
            IMAGE_DATA[unique_id] = data


def clear_image_datas():
    global IMAGE_DATA
    IMAGE_DATA.clear()


@tool(parse_docstring=True)
def image_visualizer(image_ids: List[str]) -> str:
    """Display images from RAG context to enhance user understanding.

    Call this tool when image references (e.g., img_12345678, fig_87654321, table_12345678)
    appear in local context and showing them would help the user. Only call once per set of IDs.

    Args:
        image_ids: List of image identifiers including prefixes (e.g., ["img_12345678", "fig_87654321"]).
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


@tool(parse_docstring=True)
def describe_image_content(image_id: str, user_query: str) -> str:
    """Analyze an image in relation to a user query using vision capabilities.

    Use this tool when you need to understand what is shown in an image
    in order to answer a specific user question.

    Args:
        image_id: Image identifier (for example, "img_12345678" or "fig_87654321").
        user_query: The user's question or query about the image.
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
                        "text": f"{describe_image_prompt}\n\nUser Query: {user_query}",
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
        if not response.choices[0].message.content:
            return "Error: No response received from OpenAI Vision API"

        analysis_result = response.choices[0].message.content
        logger.info(f"Successfully analyzed image: {image_id}")
        return f"Image Analysis Results:\n\n{analysis_result}"

    except Exception as e:
        error_msg = f"Error analyzing image {image_id}: {str(e)}"
        logger.error(error_msg)
        return error_msg
