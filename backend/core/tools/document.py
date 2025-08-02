from agents import function_tool
from typing import Any, Dict, List
from pathlib import Path
import os
from docx import Document
from openpyxl import Workbook
from backend.libs.logger import get_logger

import json
with open("paths.json", "r") as f:
    paths = json.load(f)
FILES_PATH = Path(paths["CREATED_DOCUMENTS_PATH"])
FILES_PATH.mkdir(parents=True, exist_ok=True)


logger = get_logger("OFFICE_TOOLS")


@function_tool
def create_excel_from_table(
    data: List[List[str]], file_name: str, sheet_name: str = "Sheet1"
) -> Dict[str, Any]:
    """
    Create an Excel file from table data.

    Args:
        data: List of lists representing table rows and columns
        file_name: Name of the Excel file to be created
        sheet_name: Name of the Excel sheet (default: "Sheet1")
    """
    try:

        # Ensure file_path is absolute and in the uploads directory
        file_path = FILES_PATH / file_name

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Create workbook and worksheet
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # Add data to worksheet
        for row_idx, row_data in enumerate(data, 1):
            for col_idx, cell_value in enumerate(row_data, 1):
                worksheet.cell(row=row_idx, column=col_idx, value=cell_value)

        # Save the workbook
        workbook.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "sheet_name": sheet_name,
            "rows": len(data),
            "columns": len(data[0]) if data else 0,
            "message": f"Excel file created successfully with {len(data)} rows",
        }

    except Exception as e:
        logger.error(f"Error creating Excel file: {str(e)}")
        return {"success": False, "error": f"Failed to create Excel file: {str(e)}"}


@function_tool
def create_word_document(content: str, file_name: str) -> Dict[str, Any]:
    """
    Create a Word document with the specified content.

    Args:
        content: Text content to be added to the document
        file_path: Name of the file to be created (without extension)
    """
    try:

        # Ensure file_path is absolute and in the uploads directory
        file_path = FILES_PATH / file_name

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Create a new document
        doc = Document()

        # Split content into paragraphs and add them
        paragraphs = content.split("\n\n")
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
        doc.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "paragraphs": len(paragraphs),
            "message": f"Word document created successfully at {file_path}",
        }

    except Exception as e:
        logger.error(f"Error creating Word document: {str(e)}")
        return {"success": False, "error": f"Failed to create Word document: {str(e)}"}
