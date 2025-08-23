from typing import List, Dict
from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, IMAGES_PATH_STR
import base64
import os
import openai
from agents import function_tool
from backend.core.prompts import redescribe_image_prompt

logger = get_logger("VISUAL")

IMAGE_DATA = []


def get_image_datas():
    return IMAGE_DATA


def set_image_datas(data):
    global IMAGE_DATA
    IMAGE_DATA = data


def clear_image_datas():
    global IMAGE_DATA
    IMAGE_DATA.clear()


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

    return "images loaded successfully into attachments. Do not add into answer, it is already in attachments."


@function_tool
def redescribe_image_content(image_name: str, user_query: str) -> str:
    """
    Analyze an image based on a user query using OpenAI's vision capabilities.

    This tool should be used when you need to understand the content of an image
    in relation to a specific user question. It will provide detailed analysis
    focused on the query context.

    Args:
        image_name: Name of the image file
        user_query: The user's question or query about the image

    Returns:
        str: Detailed analysis of the image content relevant to the query
    """

    try:
        # Construct full path
        full_path = f"{IMAGES_PATH_STR}/{image_name}"

        # Check if file exists
        if not os.path.exists(full_path):
            return f"Error: Image file not found at {full_path}"

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

        # Call OpenAI Vision API with error handling
        response = openai_client.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=1500, temperature=0.1
        )

        # Validate response
        if not response.choices or not response.choices[0].message.content:
            return "Error: No response received from OpenAI Vision API"

        analysis_result = response.choices[0].message.content
        logger.info(f"Successfully analyzed image: {image_name}")
        return f"Image Analysis Results:\n\n{analysis_result}"

    except Exception as e:
        error_msg = f"Error analyzing image {image_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg
