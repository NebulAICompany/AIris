from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import json
import uuid
import base64
from datetime import datetime
from docx import Document
from pptx import Presentation
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv
from backend.shared.logger import get_logger
from backend.shared.constants import CREATED_DOCUMENTS_PATH, openai_client
from backend.security.pii import unmask_text
from backend.core.prompts import describe_image_prompt
from langchain_core.tools import tool

load_dotenv()

GENERATED_FILES = []

FILES_PATH = Path(CREATED_DOCUMENTS_PATH)
FILES_PATH.mkdir(parents=True, exist_ok=True)

FILE_AGENT_SANDBOX_TEMPLATE = "file-agent-template"

logger = get_logger("FILE_TOOLS")


def _resolve_file_path(file_name: str) -> Path:
    """Resolve a filename to an absolute path within CREATED_DOCUMENTS_PATH.
    Strips any directory components to prevent path traversal."""
    safe_name = Path(file_name).name
    return FILES_PATH / safe_name


# ---------------------------------------------------------------------------
# Create tools
# ---------------------------------------------------------------------------

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
        if not file_name.endswith(".xlsx"):
            file_name = f"{file_name}.xlsx"

        file_path = FILES_PATH / file_name
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        unmasked_data = []
        for row_data in data:
            unmasked_row = []
            for cell_value in row_data:
                if isinstance(cell_value, str):
                    unmasked_row.append(unmask_text(cell_value))
                else:
                    unmasked_row.append(cell_value)
            unmasked_data.append(unmasked_row)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        for row_idx, row_data in enumerate(unmasked_data, 1):
            for col_idx, cell_value in enumerate(row_data, 1):
                worksheet.cell(row=row_idx, column=col_idx, value=cell_value)

        workbook.save(str(file_path))

        file_info = {
            "filename": file_name,
            "file_path": str(file_path),
            "file_type": "excel",
            "created_at": datetime.now().isoformat(),
            "message": f"Excel file created successfully with {len(unmasked_data)} rows",
        }
        set_generated_files([file_info])

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
        if not file_name.endswith(".docx"):
            file_name = f"{file_name}.docx"
        file_path = FILES_PATH / file_name
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        unmasked_content = unmask_text(content)
        doc = Document()

        paragraphs = unmasked_content.split("\n\n")
        for paragraph_text in paragraphs:
            if paragraph_text.strip():
                if len(paragraph_text.split("\n")) == 1 and len(paragraph_text) < 100:
                    doc.add_heading(paragraph_text.strip(), level=1)
                else:
                    lines = paragraph_text.split("\n")
                    for line in lines:
                        if line.strip():
                            doc.add_paragraph(line.strip())

        doc.save(str(file_path))
        file_info = {
            "filename": file_name,
            "file_path": str(file_path),
            "file_type": "word",
            "created_at": datetime.now().isoformat(),
            "message": f"Word document created successfully with {len(paragraphs)} paragraphs",
        }
        set_generated_files([file_info])

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
def create_powerpoint_from_code(code: str) -> str:
    """Create PowerPoint presentations by executing Python code in a sandboxed environment.

    Use this tool for creating PowerPoint presentations with python-pptx library.
    The code should create a Presentation object, add slides, and save the file.

    Args:
        code: Complete Python code that creates and saves a PowerPoint presentation.
            The code must include all required imports (from pptx import Presentation)
            and save the presentation to a file named 'output.pptx' (e.g., prs.save('output.pptx')).
            The saved file will be automatically moved to the documents directory.
    """
    sandbox = None
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        output_filename = f"presentation_{timestamp}_{unique_id}.pptx"
        output_path = CREATED_DOCUMENTS_PATH / output_filename

        sandbox = Sandbox.create(template=FILE_AGENT_SANDBOX_TEMPLATE, timeout=60)
        execution = sandbox.run_code(code)

        if execution.error:
            return f"Code execution error: {execution.error.value}"

        try:
            pptx_content = sandbox.files.read("/home/user/output.pptx", format="bytes")

            with open(output_path, "wb") as f:
                f.write(pptx_content)

            set_generated_files(
                [
                    {
                        "filename": output_filename,
                        "file_path": str(output_path),
                        "file_type": "powerpoint",
                        "created_at": datetime.now().isoformat(),
                        "message": f"PowerPoint presentation created successfully: {output_filename}",
                    }
                ]
            )
            return f"PowerPoint presentation created successfully: {output_filename}"
        except Exception as e:
            return f"Failed to save PowerPoint file: {str(e)}"

    except Exception as e:
        return f"Error executing code: {str(e)}"
    finally:
        if sandbox:
            try:
                sandbox.kill()
            except Exception as e:
                logger.warning(f"Failed to kill sandbox: {str(e)}")


# ---------------------------------------------------------------------------
# Modify tools
# ---------------------------------------------------------------------------

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
        doc = Document(file_path)

        unmasked_search_text = unmask_text(search_text)
        unmasked_replace_text = unmask_text(replace_text)

        replacements_made = 0

        for paragraph in doc.paragraphs:
            if unmasked_search_text in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    unmasked_search_text, unmasked_replace_text
                )
                replacements_made += 1

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if unmasked_search_text in cell.text:
                        cell.text = cell.text.replace(
                            unmasked_search_text, unmasked_replace_text
                        )
                        replacements_made += 1

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
        updates_data = json.loads(updates) if isinstance(updates, str) else updates
        wb = load_workbook(file_path)
        if sheet_name:
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                return {
                    "success": False,
                    "error": f"Worksheet '{sheet_name}' does not exist in the workbook. Available sheets: {', '.join(wb.sheetnames)}",
                }
        else:
            ws = wb.active

        for update in updates_data:
            cell_address = update["cell"]
            cell_value = update["value"]

            if isinstance(cell_value, str):
                unmasked_cell_value = unmask_text(cell_value)
                ws[cell_address] = unmasked_cell_value
            else:
                ws[cell_address] = cell_value

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
        chart_config = (json.loads(chart_data) if isinstance(chart_data, str) else chart_data)
        wb = load_workbook(file_path)
        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        chart_type = chart_config.get("type", "bar").lower()
        data_range = chart_config.get("data_range", "A1:B10")
        title = chart_config.get("title", "Chart")

        unmasked_title = unmask_text(title)

        if chart_type == "bar":
            chart = BarChart()
        elif chart_type == "line":
            chart = LineChart()
        elif chart_type == "pie":
            chart = PieChart()
        else:
            chart = BarChart()

        chart.title = unmasked_title

        if "!" in data_range:
            range_part = data_range.split("!")[-1]
        else:
            range_part = data_range

        from openpyxl.utils import range_boundaries

        min_col, min_row, max_col, max_row = range_boundaries(range_part)

        data = Reference(
            ws, min_col=min_col, min_row=min_row, max_col=max_col, max_row=max_row
        )
        chart.add_data(data, titles_from_data=True)
        ws.add_chart(chart)
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


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def read_excel_file(
    file_name: str, sheet_name: Optional[str] = None, max_rows: int = 100
) -> Dict[str, Any]:
    """Read the contents of an Excel file from the documents directory.

    Args:
        file_name: Name of the Excel file to read (must be in the created documents folder).
        sheet_name: Name of the sheet to read (None reads the active sheet).
        max_rows: Maximum number of data rows to return (default 100).
    """
    try:
        file_path = _resolve_file_path(file_name)
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_name}"}

        wb = load_workbook(str(file_path), data_only=True)

        if sheet_name:
            if sheet_name not in wb.sheetnames:
                return {
                    "success": False,
                    "error": f"Sheet '{sheet_name}' not found. Available sheets: {', '.join(wb.sheetnames)}",
                }
            ws = wb[sheet_name]
        else:
            ws = wb.active

        rows = []
        for idx, row in enumerate(ws.iter_rows(values_only=True)):
            if idx >= max_rows:
                break
            rows.append([str(cell) if cell is not None else "" for cell in row])

        total_rows = ws.max_row or 0
        truncated = total_rows > max_rows

        return {
            "success": True,
            "file_name": file_name,
            "sheet_name": ws.title,
            "all_sheets": wb.sheetnames,
            "total_rows": total_rows,
            "rows_returned": len(rows),
            "truncated": truncated,
            "data": rows,
        }

    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        return {"success": False, "error": f"Failed to read Excel file: {str(e)}"}


@tool(parse_docstring=True)
def read_word_document(file_name: str) -> Dict[str, Any]:
    """Read the contents of a Word document from the documents directory.

    Args:
        file_name: Name of the Word document to read (must be in the created documents folder).
    """
    try:
        file_path = _resolve_file_path(file_name)
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_name}"}

        doc = Document(str(file_path))

        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append({
                    "text": para.text,
                    "style": para.style.name if para.style else "Normal",
                })

        tables = []
        for table_idx, table in enumerate(doc.tables):
            table_rows = []
            for row in table.rows:
                table_rows.append([cell.text for cell in row.cells])
            tables.append({
                "table_index": table_idx,
                "rows": len(table.rows),
                "columns": len(table.columns),
                "data": table_rows,
            })

        return {
            "success": True,
            "file_name": file_name,
            "paragraph_count": len(paragraphs),
            "table_count": len(tables),
            "paragraphs": paragraphs,
            "tables": tables,
        }

    except Exception as e:
        logger.error(f"Error reading Word document: {str(e)}")
        return {"success": False, "error": f"Failed to read Word document: {str(e)}"}


@tool(parse_docstring=True)
def read_powerpoint_file(file_name: str) -> Dict[str, Any]:
    """Read the contents of a PowerPoint file from the documents directory.

    Args:
        file_name: Name of the PowerPoint file to read (must be in the created documents folder).
    """
    try:
        file_path = _resolve_file_path(file_name)
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_name}"}

        prs = Presentation(str(file_path))

        slides = []
        for slide_idx, slide in enumerate(prs.slides):
            slide_data = {
                "slide_number": slide_idx + 1,
                "layout": slide.slide_layout.name if slide.slide_layout else "Unknown",
                "shapes": [],
                "tables": [],
                "notes": "",
            }

            for shape in slide.shapes:
                if shape.has_text_frame:
                    text_content = "\n".join(
                        para.text for para in shape.text_frame.paragraphs if para.text.strip()
                    )
                    if text_content.strip():
                        slide_data["shapes"].append({
                            "name": shape.name,
                            "type": "text",
                            "content": text_content,
                        })

                if shape.has_table:
                    table = shape.table
                    table_rows = []
                    for row in table.rows:
                        table_rows.append([cell.text for cell in row.cells])
                    slide_data["tables"].append({
                        "rows": len(table.rows),
                        "columns": len(table.columns),
                        "data": table_rows,
                    })

            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                slide_data["notes"] = slide.notes_slide.notes_text_frame.text

            slides.append(slide_data)

        return {
            "success": True,
            "file_name": file_name,
            "slide_count": len(slides),
            "slides": slides,
        }

    except Exception as e:
        logger.error(f"Error reading PowerPoint file: {str(e)}")
        return {"success": False, "error": f"Failed to read PowerPoint file: {str(e)}"}


# ---------------------------------------------------------------------------
# Image understanding
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def describe_file_image(file_name: str, query: str) -> str:
    """Analyze an image file from the documents directory using vision AI.

    Use this tool to understand what is shown in an image (PNG, JPG) that exists
    in the created documents folder.

    Args:
        file_name: Name of the image file to analyze (must be in the created documents folder).
        query: A question or description of what you want to understand about the image.
    """
    try:
        file_path = _resolve_file_path(file_name)
        if not file_path.exists():
            return f"Error: Image file not found: {file_name}"

        ext = file_path.suffix.lower()
        supported = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
        if ext not in supported:
            return f"Error: Unsupported image format '{ext}'. Supported: {', '.join(supported)}"

        with open(file_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")

        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(ext, "image/png")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{describe_image_prompt}\n\nUser Query: {query}",
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

        if not response.choices[0].message.content:
            return "Error: No response received from Vision API"

        analysis = response.choices[0].message.content
        logger.info(f"Successfully analyzed image: {file_name}")
        return f"Image Analysis Results:\n\n{analysis}"

    except Exception as e:
        error_msg = f"Error analyzing image {file_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg


# ---------------------------------------------------------------------------
# General sandbox
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def execute_file_code(code: str, output_filenames: List[str]) -> Dict[str, Any]:
    """Execute Python code in a sandboxed environment to create or process files.

    The sandbox has python-pptx, openpyxl, python-docx, and Pillow pre-installed.
    Use this for complex file operations that go beyond what the dedicated tools offer.
    Each output file must be saved under /home/user/ in the sandbox.

    Args:
        code: Complete Python code to execute. Must save output files under /home/user/.
        output_filenames: List of filenames the code will produce under /home/user/ (e.g. ["report.docx", "chart.png"]).
    """
    sandbox = None
    try:
        sandbox = Sandbox.create(template=FILE_AGENT_SANDBOX_TEMPLATE, timeout=60)
        execution = sandbox.run_code(code)

        if execution.error:
            return {
                "success": False,
                "error": f"Code execution error: {execution.error.value}",
            }

        saved_files = []
        errors = []

        for fname in output_filenames:
            safe_name = Path(fname).name
            sandbox_path = f"/home/user/{safe_name}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            stem = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            local_name = f"{stem}_{timestamp}_{unique_id}{suffix}"
            local_path = FILES_PATH / local_name

            try:
                content = sandbox.files.read(sandbox_path, format="bytes")
                with open(local_path, "wb") as f:
                    f.write(content)

                ext = suffix.lower()
                type_map = {
                    ".xlsx": "excel", ".xls": "excel",
                    ".docx": "word", ".doc": "word",
                    ".pptx": "powerpoint",
                    ".png": "image", ".jpg": "image", ".jpeg": "image",
                    ".pdf": "pdf", ".csv": "csv", ".txt": "text",
                }
                file_type = type_map.get(ext, "unknown")

                file_info = {
                    "filename": local_name,
                    "file_path": str(local_path),
                    "file_type": file_type,
                    "created_at": datetime.now().isoformat(),
                    "message": f"File created via sandbox: {local_name}",
                }
                set_generated_files([file_info])
                saved_files.append(file_info)

            except Exception as e:
                errors.append(f"Failed to retrieve '{fname}': {str(e)}")

        stdout = ""
        if execution.logs and execution.logs.stdout:
            stdout = "\n".join(execution.logs.stdout)

        result = {
            "success": len(saved_files) > 0,
            "files_created": saved_files,
            "stdout": stdout,
        }
        if errors:
            result["errors"] = errors
        return result

    except Exception as e:
        return {"success": False, "error": f"Sandbox error: {str(e)}"}
    finally:
        if sandbox:
            try:
                sandbox.kill()
            except Exception as e:
                logger.warning(f"Failed to kill sandbox: {str(e)}")


# ---------------------------------------------------------------------------
# List files
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def list_created_files() -> Dict[str, Any]:
    """List all created files in the documents directory.

    Returns a list of all files that have been created, including their names and full paths.
    This helps track which files are available and where they are located.
    """
    try:
        created_files = []

        if FILES_PATH.exists() and FILES_PATH.is_dir():
            for file_path in FILES_PATH.iterdir():
                if file_path.is_file():
                    extension = file_path.suffix.lower()
                    type_map = {
                        ".xlsx": "excel", ".xls": "excel",
                        ".docx": "word", ".doc": "word",
                        ".pptx": "powerpoint",
                        ".pdf": "pdf",
                        ".txt": "text",
                        ".csv": "csv",
                        ".png": "image", ".jpg": "image", ".jpeg": "image",
                        ".gif": "image", ".bmp": "image",
                    }
                    file_type = type_map.get(extension, "unknown")

                    created_files.append({
                        "filename": file_path.name,
                        "file_path": str(file_path),
                        "file_type": file_type,
                        "extension": extension,
                    })

        return {
            "success": True,
            "count": len(created_files),
            "files": created_files,
            "message": f"Found {len(created_files)} created file(s) in the documents directory.",
        }

    except Exception as e:
        logger.error(f"Error listing created files: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list created files: {str(e)}",
            "files": [],
        }


# ---------------------------------------------------------------------------
# Generated files tracking helpers
# ---------------------------------------------------------------------------

def get_generated_files() -> Dict[str, Any]:
    global GENERATED_FILES
    return GENERATED_FILES


def clear_generated_files():
    global GENERATED_FILES
    GENERATED_FILES.clear()


def set_generated_files(files: List[Dict[str, Any]]):
    global GENERATED_FILES
    GENERATED_FILES.extend(files)
