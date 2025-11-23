from typing import Any, Dict, List
from pathlib import Path
import os
import json
from datetime import datetime
from docx import Document
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from pptx import Presentation
from backend.shared.logger import get_logger
from backend.shared.constants import CREATED_DOCUMENTS_PATH
from backend.security.pii import unmask_text
from langchain_core.tools import tool

# Global variable to track generated files
GENERATED_FILES = []

FILES_PATH = Path(CREATED_DOCUMENTS_PATH)
FILES_PATH.mkdir(parents=True, exist_ok=True)


logger = get_logger("OFFICE_TOOLS")


@tool
def create_excel_file(
    data: List[List[str]], file_name: str, sheet_name: str = "Sheet1"
) -> Dict[str, Any]:
    """
    Create an Excel file from table data.

    Args:
        data: List of lists representing table rows and columns
        file_name: Name of the Excel file to be created
        sheet_name: Name of the Excel sheet (default: "Sheet1")

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - file_path (str): Full path to the created Excel file (if successful)
            - sheet_name (str): Name of the created sheet (if successful)
            - rows (int): Number of rows in the data (if successful)
            - columns (int): Number of columns in the data (if successful)
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        # Add .xlsx extension if not present
        if not file_name.endswith(".xlsx"):
            file_name = f"{file_name}.xlsx"

        # Ensure file_path is absolute and in the uploads directory
        file_path = FILES_PATH / file_name

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Unmask PII data before creating Excel file
        unmasked_data = []
        for row_data in data:
            unmasked_row = []
            for cell_value in row_data:
                if isinstance(cell_value, str):
                    unmasked_row.append(unmask_text(cell_value))
                else:
                    unmasked_row.append(cell_value)
            unmasked_data.append(unmasked_row)

        # Create workbook and worksheet
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # Add unmasked data to worksheet
        for row_idx, row_data in enumerate(unmasked_data, 1):
            for col_idx, cell_value in enumerate(row_data, 1):
                worksheet.cell(row=row_idx, column=col_idx, value=cell_value)

        # Save the workbook
        workbook.save(str(file_path))

        # Add to generated files list
        file_info = {
            "filename": file_name,
            "file_path": str(file_path),
            "file_type": "excel",
            "created_at": datetime.now().isoformat(),
            "message": f"Excel file created successfully with {len(unmasked_data)} rows",
        }
        GENERATED_FILES.append(file_info)

        return {
            "success": True,
            "file_path": str(file_path),
            "sheet_name": sheet_name,
            "rows": len(data),
            "columns": len(data[0]) if data else 0,
            "message": f"Excel file created successfully with {len(data)} rows. File loaded successfully into attachments. You can view it directly from the attachments section below.",
            "file_info": file_info,
        }

    except Exception as e:
        logger.error(f"Error creating Excel file: {str(e)}")
        return {"success": False, "error": f"Failed to create Excel file: {str(e)}"}


@tool
def create_word_document(content: str, file_name: str) -> Dict[str, Any]:
    """
    Create a Word document with the specified content.

    Args:
        content: Text content to be added to the document
        file_name: Name of the file to be created

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - file_path (str): Full path to the created Word document (if successful)
            - paragraphs (int): Number of paragraphs created (if successful)
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        # Add .docx extension if not present
        if not file_name.endswith(".docx"):
            file_name = f"{file_name}.docx"

        # Ensure file_path is absolute and in the uploads directory
        file_path = FILES_PATH / file_name

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Unmask PII data before creating Word document
        unmasked_content = unmask_text(content)

        # Create a new document
        doc = Document()

        # Split unmasked content into paragraphs and add them
        paragraphs = unmasked_content.split("\n\n")
        for paragraph_text in paragraphs:
            if paragraph_text.strip():
                # Check if it's a title (simple heuristic)
                if len(paragraph_text.split("\n")) == 1 and len(paragraph_text) < 100:
                    doc.add_heading(paragraph_text.strip(), level=1)
                else:
                    # Handle multi-line paragraphs
                    lines = paragraph_text.split("\n")
                    for line in lines:
                        if line.strip():
                            doc.add_paragraph(line.strip())

        # Save the document
        doc.save(str(file_path))

        # Add to generated files list
        file_info = {
            "filename": file_name,
            "file_path": str(file_path),
            "file_type": "word",
            "created_at": datetime.now().isoformat(),
            "message": f"Word document created successfully with {len(paragraphs)} paragraphs",
        }
        GENERATED_FILES.append(file_info)

        return {
            "success": True,
            "file_path": str(file_path),
            "paragraphs": len(paragraphs),
            "message": f"Word document created successfully with {len(paragraphs)} paragraphs. File loaded successfully into attachments. You can view it directly from the attachments section below.",
            "file_info": file_info,
        }

    except Exception as e:
        logger.error(f"Error creating Word document: {str(e)}")
        return {"success": False, "error": f"Failed to create Word document: {str(e)}"}


@tool
def create_powerpoint_presentation(
    title: str, slides_content: str, file_name: str
) -> Dict[str, Any]:
    """
    Create a PowerPoint presentation with multiple slides for investment committee presentations and client meetings.

    Args:
        title: Title of the presentation
        slides_content: JSON string containing list of dictionaries with 'title' and 'content' keys for each slide
        file_name: Name of the PowerPoint file to be created

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - file_path (str): Full path to the created PowerPoint file (if successful)
            - slides_count (int): Total number of slides including title slide (if successful)
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        # Parse JSON string
        slides_data = (
            json.loads(slides_content)
            if isinstance(slides_content, str)
            else slides_content
        )

        # Add .pptx extension if not present
        if not file_name.endswith(".pptx"):
            file_name = f"{file_name}.pptx"

        # Ensure file_path is absolute and in the documents directory
        file_path = FILES_PATH / file_name

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Create presentation
        prs = Presentation()

        # Unmask PII data before creating PowerPoint presentation
        unmasked_title = unmask_text(title)

        # Add title slide
        title_slide_layout = prs.slide_layouts[0]  # Title slide layout
        slide = prs.slides.add_slide(title_slide_layout)
        title_shape = slide.shapes.title
        title_shape.text = unmasked_title

        # Add content slides
        for slide_data in slides_data:
            slide_layout = prs.slide_layouts[1]  # Title and content layout
            slide = prs.slides.add_slide(slide_layout)

            # Set slide title
            if "title" in slide_data:
                unmasked_slide_title = unmask_text(slide_data["title"])
                slide.shapes.title.text = unmasked_slide_title

            # Set slide content
            if "content" in slide_data:
                content_placeholder = slide.placeholders[1]
                unmasked_slide_content = unmask_text(slide_data["content"])
                content_placeholder.text = unmasked_slide_content

        # Save presentation
        prs.save(str(file_path))

        # Add to generated files list
        file_info = {
            "filename": file_name,
            "file_path": str(file_path),
            "file_type": "powerpoint",
            "created_at": datetime.now().isoformat(),
            "message": f"PowerPoint presentation created successfully with {len(slides_data) + 1} slides",
        }
        GENERATED_FILES.append(file_info)

        return {
            "success": True,
            "file_path": str(file_path),
            "slides_count": len(slides_data) + 1,  # +1 for title slide
            "message": f"PowerPoint presentation created successfully with {len(slides_data) + 1} slides. File loaded successfully into attachments. You can view it directly from the attachments section below.",
            "file_info": file_info,
        }

    except Exception as e:
        logger.error(f"Error creating PowerPoint presentation: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to create PowerPoint presentation: {str(e)}",
        }


@tool
def add_powerpoint_slide(
    file_path: str, slide_title: str, slide_content: str, slide_position: int = -1
) -> Dict[str, Any]:
    """
    Add a new slide to an existing PowerPoint presentation for dynamic slide addition and template-based expansion.

    Args:
        file_path: Path to the existing PowerPoint file
        slide_title: Title of the new slide
        slide_content: Content of the new slide
        slide_position: Position to insert the slide (-1 for end)

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - file_path (str): Path to the updated PowerPoint file (if successful)
            - total_slides (int): Total number of slides in the presentation (if successful)
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        # Load existing presentation
        prs = Presentation(file_path)

        # Create new slide
        slide_layout = prs.slide_layouts[1]  # Title and content layout

        if slide_position == -1:
            slide = prs.slides.add_slide(slide_layout)
        else:
            slide = prs.slides.add_slide(slide_layout)
            # Move slide to desired position (simplified approach)

        # Unmask PII data before adding slide
        unmasked_slide_title = unmask_text(slide_title)
        unmasked_slide_content = unmask_text(slide_content)

        # Set slide content
        slide.shapes.title.text = unmasked_slide_title
        content_placeholder = slide.placeholders[1]
        content_placeholder.text = unmasked_slide_content

        # Save presentation
        prs.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "total_slides": len(prs.slides),
            "message": f"Slide added successfully. Presentation now has {len(prs.slides)} slides.",
        }

    except Exception as e:
        logger.error(f"Error adding slide to PowerPoint: {str(e)}")
        return {"success": False, "error": f"Failed to add slide: {str(e)}"}


@tool
def modify_word_content(
    file_path: str, search_text: str, replace_text: str
) -> Dict[str, Any]:
    """
    Modify existing Word documents for updates and revisions.

    Args:
        file_path: Path to the Word document
        search_text: Text to search for
        replace_text: Text to replace with

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - file_path (str): Path to the updated Word document (if successful)
            - replacements_made (int): Number of text replacements made (if successful)
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        # Load document
        doc = Document(file_path)

        # Unmask PII data before modifying Word document
        unmasked_search_text = unmask_text(search_text)
        unmasked_replace_text = unmask_text(replace_text)

        replacements_made = 0

        # Replace text in paragraphs
        for paragraph in doc.paragraphs:
            if unmasked_search_text in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    unmasked_search_text, unmasked_replace_text
                )
                replacements_made += 1

        # Replace text in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if unmasked_search_text in cell.text:
                        cell.text = cell.text.replace(
                            unmasked_search_text, unmasked_replace_text
                        )
                        replacements_made += 1

        # Save document
        doc.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "replacements_made": replacements_made,
            "message": f"Document updated successfully. Made {replacements_made} replacements.",
        }

    except Exception as e:
        logger.error(f"Error modifying Word document: {str(e)}")
        return {"success": False, "error": f"Failed to modify Word document: {str(e)}"}


@tool
def modify_excel_cells(
    file_path: str, updates: str, sheet_name: str = None
) -> Dict[str, Any]:
    """
    Update cell values in Excel for financial model parameters.

    Args:
        file_path: Path to the Excel file
        updates: JSON string containing list of dictionaries with 'cell', 'value' keys (e.g., "[{'cell': 'A1', 'value': 100}]")
        sheet_name: Name of the sheet to modify (None for active sheet)

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - file_path (str): Path to the updated Excel file (if successful)
            - updates_applied (int): Number of cell updates applied (if successful)
            - sheet_name (str): Name of the modified sheet (if successful)
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        # Parse JSON string
        updates_data = json.loads(updates) if isinstance(updates, str) else updates

        # Load workbook
        wb = load_workbook(file_path)

        # Select sheet
        if sheet_name:
            # Check if the specified sheet exists in the workbook
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                return {
                    "success": False,
                    "error": f"Worksheet '{sheet_name}' does not exist in the workbook. Available sheets: {', '.join(wb.sheetnames)}",
                }
        else:
            ws = wb.active

        # Select sheet
        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        # Apply updates with PII unmasking
        for update in updates_data:
            cell_address = update["cell"]
            cell_value = update["value"]

            # Unmask PII data if the value is a string
            if isinstance(cell_value, str):
                unmasked_cell_value = unmask_text(cell_value)
                ws[cell_address] = unmasked_cell_value
            else:
                ws[cell_address] = cell_value

        # Save workbook
        wb.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "updates_applied": len(updates_data),
            "sheet_name": ws.title,
            "message": f"Successfully updated {len(updates_data)} cells in sheet '{ws.title}'",
        }

    except Exception as e:
        logger.error(f"Error modifying Excel cells: {str(e)}")
        return {"success": False, "error": f"Failed to modify Excel cells: {str(e)}"}


@tool
def create_excel_charts(
    file_path: str, chart_data: str, sheet_name: str = None
) -> Dict[str, Any]:
    """
    Create performance charts, risk visualizations, and correlation heatmaps in Excel.

    Args:
        file_path: Path to the Excel file
        chart_data: JSON string containing chart configuration dictionary
        sheet_name: Name of the sheet (None for active sheet)

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - file_path (str): Path to the updated Excel file (if successful)
            - chart_type (str): Type of chart created (if successful)
            - chart_title (str): Title of the created chart (if successful)
            - sheet_name (str): Name of the sheet where chart was added (if successful)
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        # Parse JSON string
        chart_config = (
            json.loads(chart_data) if isinstance(chart_data, str) else chart_data
        )

        # Load workbook
        wb = load_workbook(file_path)

        # Select sheet
        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        chart_type = chart_config.get("type", "bar").lower()
        data_range = chart_config.get("data_range", "A1:B10")
        title = chart_config.get("title", "Chart")

        # Unmask PII data in chart title
        unmasked_title = unmask_text(title)

        # Create chart based on type
        if chart_type == "bar":
            chart = BarChart()
        elif chart_type == "line":
            chart = LineChart()
        elif chart_type == "pie":
            chart = PieChart()
        else:
            chart = BarChart()  # Default to bar chart

        # Set chart properties
        chart.title = unmasked_title

        # Add data to chart
        # Parse the range string to get min/max coordinates
        if "!" in data_range:
            range_part = data_range.split("!")[-1]
        else:
            range_part = data_range

        # Convert range like "A1:B10" to coordinates
        from openpyxl.utils import range_boundaries

        min_col, min_row, max_col, max_row = range_boundaries(range_part)

        data = Reference(
            ws, min_col=min_col, min_row=min_row, max_col=max_col, max_row=max_row
        )
        chart.add_data(data, titles_from_data=True)

        # Add chart to worksheet
        ws.add_chart(chart)

        # Save workbook
        wb.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "chart_type": chart_type,
            "chart_title": title,
            "sheet_name": ws.title,
            "message": f"Successfully created {chart_type} chart '{title}' in sheet '{ws.title}'",
        }

    except Exception as e:
        logger.error(f"Error creating Excel chart: {str(e)}")
        return {"success": False, "error": f"Failed to create Excel chart: {str(e)}"}


def get_generated_files() -> Dict[str, Any]:
    global GENERATED_FILES
    return GENERATED_FILES


def clear_generated_files():
    global GENERATED_FILES
    GENERATED_FILES.clear()
