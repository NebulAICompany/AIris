from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import json
from datetime import datetime
from docx import Document
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from backend.shared.logger import get_logger
from backend.shared.constants import CREATED_DOCUMENTS_PATH
from backend.security.pii import unmask_text
from langchain_core.tools import tool

# Global variable to track generated files
GENERATED_FILES = []

FILES_PATH = Path(CREATED_DOCUMENTS_PATH)
FILES_PATH.mkdir(parents=True, exist_ok=True)


logger = get_logger("OFFICE_TOOLS")

@tool(parse_docstring=True)
def create_excel_file(
    data: List[List[str]],
    file_name: str,
    sheet_name: str = "Sheet1",
) -> Dict[str, Any]:
    """Create an Excel file from table data.

    Args:
        data: List of rows, where each row is a list of cell values.
        file_name: Name of the Excel file to create.
        sheet_name: Name of the Excel sheet (default "Sheet1").
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


@tool(parse_docstring=True)
def create_word_document(content: str, file_name: str) -> Dict[str, Any]:
    """Create a Word document with the specified content.

    Args:
        content: Text content to add to the document.
        file_name: Name of the Word document file to create.
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


@tool(parse_docstring=True)
def modify_word_content(
    file_path: str, search_text: str, replace_text: str
) -> Dict[str, Any]:
    """Modify an existing Word document by searching and replacing text.

    Args:
        file_path: Path to the Word document to update.
        search_text: Text to search for in the document.
        replace_text: Text that will replace each occurrence of the search text.
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


@tool(parse_docstring=True)
def modify_excel_cells(
    file_path: str, updates: str, sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """Update cell values in an Excel file.

    Args:
        file_path: Path to the Excel file.
        updates: JSON string with a list of objects containing 'cell' and 'value' keys. Example: "[{'cell': 'A1', 'value': 100}]".
        sheet_name: Name of the sheet to modify (None for the active sheet).
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


@tool(parse_docstring=True)
def create_excel_charts(
    file_path: str, chart_data: str, sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """Create charts in an Excel workbook.

    Args:
        file_path: Path to the Excel file to update.
        chart_data: JSON string with the chart configuration (for example,
            chart type, ranges, and titles).
        sheet_name: Name of the sheet to add the chart to (None for the active sheet).
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
