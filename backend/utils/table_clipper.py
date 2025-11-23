import os
import re
import io
from typing import List, Tuple
from PIL import Image
import fitz
from pathlib import Path
import hashlib

try:
    from backend.shared.logger import get_logger
except ImportError:
    from shared.logger import get_logger

logger = get_logger("TABLE_CLIPPER")


def render_pdf_page_to_image(
    pdf_path: str, page_number: int, dpi: int = 300
) -> Image.Image:
    """Render a PDF page to PIL Image."""
    doc = fitz.open(pdf_path)
    if page_number < 1 or page_number > len(doc):
        raise ValueError(f"Page number {page_number} is out of range (1-{len(doc)})")

    page = doc[page_number - 1]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    doc.close()
    return Image.open(io.BytesIO(img_data))


def parse_polygon_coordinates(formatted_polygon: str) -> List[Tuple[float, float]]:
    """Parse polygon coordinates from formatted string."""
    pattern = r"\[([0-9.-]+),\s*([0-9.-]+)\]"
    matches = re.findall(pattern, formatted_polygon)
    return [(float(x), float(y)) for x, y in matches]


def clip_table_from_page_image(
    page_image: Image.Image,
    polygon_coordinates: List[Tuple[float, float]],
    margin: int = 10,
    padding_inches: float = 0.1,
) -> Image.Image:
    """Clip table region from page image based on polygon coordinates."""
    img_width, img_height = page_image.size

    # Find bounding box
    x_coords = [coord[0] for coord in polygon_coordinates]
    y_coords = [coord[1] for coord in polygon_coordinates]
    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)

    # Add padding
    min_x -= padding_inches
    max_x += padding_inches
    min_y -= padding_inches
    max_y += padding_inches

    # Convert to pixels (300 DPI)
    dpi = 300
    left = max(0, int(min_x * dpi) - margin)
    top = max(0, int(min_y * dpi) - margin)
    right = min(img_width, int(max_x * dpi) + margin)
    bottom = min(img_height, int(max_y * dpi) + margin)

    return page_image.crop((left, top, right, bottom))


def extract_table_images_from_pdf(
    pdf_path: str,
    table_regions: List[dict],
    output_dir: str = "clipped_tables",
    dpi: int = 300,
    padding_inches: float = 0.1,
) -> List[str]:
    """Extract table images from PDF based on bounding regions."""
    os.makedirs(output_dir, exist_ok=True)
    pdf_name = Path(pdf_path).stem
    saved_images = []

    for region_info in table_regions:
        page_number = region_info["page_number"]
        polygon_str = region_info["polygon"]
        table_id = region_info.get("table_id", f"table_{len(saved_images)}")

        # Render page and clip table
        page_image = render_pdf_page_to_image(pdf_path, page_number, dpi)
        polygon_coords = parse_polygon_coordinates(polygon_str)
        table_image = clip_table_from_page_image(
            page_image, polygon_coords, padding_inches=padding_inches
        )

        # Create unique identifier for table
        unique_id = hashlib.sha256(
            f"{pdf_name}_{page_number}_{table_id}".encode()
        ).hexdigest()[:8]
        output_filename = f"table_{unique_id}.png"
        output_path = os.path.join(output_dir, output_filename)
        table_image.save(output_path, "PNG")
        saved_images.append(output_path)
        logger.info(f"Saved table image: {output_filename}")

    return saved_images


def create_table_regions_from_azure_result(azure_result) -> List[dict]:
    """Create table regions list from Azure Document Intelligence result."""
    if not azure_result.tables:
        return []

    table_regions = []
    for table_idx, table in enumerate(azure_result.tables):
        if table.bounding_regions:
            for region in table.bounding_regions:
                polygon_str = ", ".join(
                    [
                        f"[{region.polygon[i]}, {region.polygon[i + 1]}]"
                        for i in range(0, len(region.polygon), 2)
                    ]
                )

                table_regions.append(
                    {
                        "table_id": f"table_{table_idx}",
                        "page_number": region.page_number,
                        "polygon": polygon_str,
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                    }
                )

    return table_regions
