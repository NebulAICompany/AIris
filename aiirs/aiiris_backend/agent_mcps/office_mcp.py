#!/usr/bin/env python3
"""
Office MCP Server - Microsoft Office operations via MCP
Supports Word, Excel, PowerPoint operations using stdio transport
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import traceback

# Office-related imports
try:
    import win32com.client as win32
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("Warning: win32com.client not available. Office operations will be limited.")

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Inches
    
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# MCP Protocol imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP not available. Please install: pip install mcp")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OfficeOperations:
    """Core Office operations using win32com and alternative libraries"""
    
    def __init__(self):
        self.word_app = None
        self.excel_app = None
        self.powerpoint_app = None
        
    def _get_word_app(self):
        """Get Word application instance"""
        if not WIN32_AVAILABLE:
            return None
        try:
            if not self.word_app:
                self.word_app = win32.Dispatch("Word.Application")
                self.word_app.Visible = False
            return self.word_app
        except Exception as e:
            logger.error(f"Failed to get Word application: {e}")
            return None
    
    def _get_excel_app(self):
        """Get Excel application instance"""
        if not WIN32_AVAILABLE:
            return None
        try:
            if not self.excel_app:
                self.excel_app = win32.Dispatch("Excel.Application")
                self.excel_app.Visible = False
            return self.excel_app
        except Exception as e:
            logger.error(f"Failed to get Excel application: {e}")
            return None
    
    def _get_powerpoint_app(self):
        """Get PowerPoint application instance"""
        if not WIN32_AVAILABLE:
            return None
        try:
            if not self.powerpoint_app:
                self.powerpoint_app = win32.Dispatch("PowerPoint.Application")
                self.powerpoint_app.Visible = False
            return self.powerpoint_app
        except Exception as e:
            logger.error(f"Failed to get PowerPoint application: {e}")
            return None
    
    def convert_word_to_pdf(self, word_path: str, pdf_path: str) -> Dict[str, Any]:
        """Convert Word document to PDF"""
        try:
            word_path = os.path.abspath(word_path)
            pdf_path = os.path.abspath(pdf_path)
            
            if not os.path.exists(word_path):
                return {"success": False, "error": f"Word file not found: {word_path}"}
            
            word_app = self._get_word_app()
            if not word_app:
                return {"success": False, "error": "Word application not available"}
            
            # Open document
            doc = word_app.Documents.Open(word_path)
            
            # Save as PDF (wdFormatPDF = 17)
            doc.SaveAs2(pdf_path, FileFormat=17)
            doc.Close()
            
            return {
                "success": True,
                "message": f"Successfully converted {word_path} to {pdf_path}",
                "input_file": word_path,
                "output_file": pdf_path
            }
            
        except Exception as e:
            logger.error(f"Error converting Word to PDF: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_word_tables(self, word_path: str) -> Dict[str, Any]:
        """Extract tables from Word document"""
        try:
            word_path = os.path.abspath(word_path)
            
            if not os.path.exists(word_path):
                return {"success": False, "error": f"Word file not found: {word_path}"}
            
            tables_data = []
            
            if PYTHON_DOCX_AVAILABLE:
                # Use python-docx for table extraction
                doc = Document(word_path)
                
                for i, table in enumerate(doc.tables):
                    table_data = []
                    for row in table.rows:
                        row_data = []
                        for cell in row.cells:
                            row_data.append(cell.text.strip())
                        table_data.append(row_data)
                    
                    tables_data.append({
                        "table_index": i,
                        "data": table_data,
                        "rows": len(table_data),
                        "columns": len(table_data[0]) if table_data else 0
                    })
            
            elif WIN32_AVAILABLE:
                # Fallback to win32com
                word_app = self._get_word_app()
                if word_app:
                    doc = word_app.Documents.Open(word_path)
                    
                    for i in range(doc.Tables.Count):
                        table = doc.Tables(i + 1)  # COM is 1-indexed
                        table_data = []
                        
                        for row in range(1, table.Rows.Count + 1):
                            row_data = []
                            for col in range(1, table.Columns.Count + 1):
                                try:
                                    cell_text = table.Cell(row, col).Range.Text.strip()
                                    row_data.append(cell_text)
                                except:
                                    row_data.append("")
                            table_data.append(row_data)
                        
                        tables_data.append({
                            "table_index": i,
                            "data": table_data,
                            "rows": len(table_data),
                            "columns": len(table_data[0]) if table_data else 0
                        })
                    
                    doc.Close()
            
            return {
                "success": True,
                "tables": tables_data,
                "table_count": len(tables_data),
                "source_file": word_path
            }
            
        except Exception as e:
            logger.error(f"Error extracting Word tables: {e}")
            return {"success": False, "error": str(e)}
    
    def create_excel_from_table(self, table_data: List[List[str]], excel_path: str, sheet_name: str = "Sheet1") -> Dict[str, Any]:
        """Create Excel file from table data"""
        try:
            excel_path = os.path.abspath(excel_path)
            
            if OPENPYXL_AVAILABLE:
                # Use openpyxl
                wb = Workbook()
                ws = wb.active
                ws.title = sheet_name
                
                for row in table_data:
                    ws.append(row)
                
                wb.save(excel_path)
                
            elif WIN32_AVAILABLE:
                # Fallback to win32com
                excel_app = self._get_excel_app()
                if not excel_app:
                    return {"success": False, "error": "Excel application not available"}
                
                wb = excel_app.Workbooks.Add()
                ws = wb.Worksheets(1)
                ws.Name = sheet_name
                
                for i, row in enumerate(table_data, 1):
                    for j, cell_value in enumerate(row, 1):
                        ws.Cells(i, j).Value = cell_value
                
                wb.SaveAs(excel_path)
                wb.Close()
            
            else:
                return {"success": False, "error": "No Excel library available"}
            
            return {
                "success": True,
                "message": f"Excel file created successfully: {excel_path}",
                "file_path": excel_path,
                "sheet_name": sheet_name,
                "rows": len(table_data),
                "columns": len(table_data[0]) if table_data else 0
            }
            
        except Exception as e:
            logger.error(f"Error creating Excel file: {e}")
            return {"success": False, "error": str(e)}
    
    def read_excel_file(self, excel_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """Read Excel file and return data"""
        try:
            excel_path = os.path.abspath(excel_path)
            
            if not os.path.exists(excel_path):
                return {"success": False, "error": f"Excel file not found: {excel_path}"}
            
            if PANDAS_AVAILABLE:
                # Use pandas for reading
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                data = df.values.tolist()
                headers = df.columns.tolist()
                
                return {
                    "success": True,
                    "data": data,
                    "headers": headers,
                    "rows": len(data),
                    "columns": len(headers),
                    "sheet_name": sheet_name or "Sheet1"
                }
                
            elif OPENPYXL_AVAILABLE:
                # Use openpyxl
                wb = load_workbook(excel_path)
                ws = wb[sheet_name] if sheet_name else wb.active
                
                data = []
                for row in ws.iter_rows(values_only=True):
                    data.append(list(row))
                
                return {
                    "success": True,
                    "data": data,
                    "rows": len(data),
                    "columns": len(data[0]) if data else 0,
                    "sheet_name": ws.title
                }
            
            else:
                return {"success": False, "error": "No Excel reading library available"}
                
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return {"success": False, "error": str(e)}
    
    def create_word_document(self, content: str, file_path: str) -> Dict[str, Any]:
        """Create a new Word document"""
        try:
            file_path = os.path.abspath(file_path)
            
            if PYTHON_DOCX_AVAILABLE:
                # Use python-docx
                doc = Document()
                doc.add_paragraph(content)
                doc.save(file_path)
                
            elif WIN32_AVAILABLE:
                # Fallback to win32com
                word_app = self._get_word_app()
                if not word_app:
                    return {"success": False, "error": "Word application not available"}
                
                doc = word_app.Documents.Add()
                doc.Content.Text = content
                doc.SaveAs2(file_path)
                doc.Close()
            
            else:
                return {"success": False, "error": "No Word library available"}
            
            return {
                "success": True,
                "message": f"Word document created successfully: {file_path}",
                "file_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Error creating Word document: {e}")
            return {"success": False, "error": str(e)}
    
    def get_available_apps(self) -> Dict[str, Any]:
        """Check which Office applications are available"""
        apps = {
            "word": False,
            "excel": False,
            "powerpoint": False,
            "libraries": {
                "win32com": WIN32_AVAILABLE,
                "openpyxl": OPENPYXL_AVAILABLE,
                "python_docx": PYTHON_DOCX_AVAILABLE,
                "pandas": PANDAS_AVAILABLE
            }
        }
        
        if WIN32_AVAILABLE:
            try:
                self._get_word_app()
                apps["word"] = True
            except:
                pass
            
            try:
                self._get_excel_app()
                apps["excel"] = True
            except:
                pass
            
            try:
                self._get_powerpoint_app()
                apps["powerpoint"] = True
            except:
                pass
        
        return {"success": True, "available_apps": apps}
    
    def cleanup(self):
        """Clean up COM objects"""
        if WIN32_AVAILABLE:
            try:
                if self.word_app:
                    self.word_app.Quit()
                if self.excel_app:
                    self.excel_app.Quit()
                if self.powerpoint_app:
                    self.powerpoint_app.Quit()
            except:
                pass


class OfficeMCPServer:
    """Office MCP Server implementation"""
    
    def __init__(self):
        self.office_ops = OfficeOperations()
        if not MCP_AVAILABLE:
            raise ImportError("MCP not available. Please install: pip install mcp")
        
        self.server = Server("office-mcp")
        self._setup_tools()
    
    def _setup_tools(self):
        """Setup MCP tools"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="convert_word_to_pdf",
                    description="Convert a Word document to PDF format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "word_path": {
                                "type": "string",
                                "description": "Path to the Word document"
                            },
                            "pdf_path": {
                                "type": "string",
                                "description": "Path for the output PDF file"
                            }
                        },
                        "required": ["word_path", "pdf_path"]
                    }
                ),
                Tool(
                    name="extract_word_tables",
                    description="Extract tables from a Word document",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "word_path": {
                                "type": "string",
                                "description": "Path to the Word document"
                            }
                        },
                        "required": ["word_path"]
                    }
                ),
                Tool(
                    name="create_excel_from_table",
                    description="Create an Excel file from table data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_data": {
                                "type": "array",
                                "description": "2D array of table data",
                                "items": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "excel_path": {
                                "type": "string",
                                "description": "Path for the output Excel file"
                            },
                            "sheet_name": {
                                "type": "string",
                                "description": "Name of the Excel sheet",
                                "default": "Sheet1"
                            }
                        },
                        "required": ["table_data", "excel_path"]
                    }
                ),
                Tool(
                    name="read_excel_file",
                    description="Read data from an Excel file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "excel_path": {
                                "type": "string",
                                "description": "Path to the Excel file"
                            },
                            "sheet_name": {
                                "type": "string",
                                "description": "Name of the sheet to read (optional)"
                            }
                        },
                        "required": ["excel_path"]
                    }
                ),
                Tool(
                    name="create_word_document",
                    description="Create a new Word document with content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Text content for the document"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Path for the output Word document"
                            }
                        },
                        "required": ["content", "file_path"]
                    }
                ),
                Tool(
                    name="get_available_apps",
                    description="Get information about available Office applications",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                result = None
                
                if name == "convert_word_to_pdf":
                    result = self.office_ops.convert_word_to_pdf(
                        arguments["word_path"],
                        arguments["pdf_path"]
                    )
                
                elif name == "extract_word_tables":
                    result = self.office_ops.extract_word_tables(
                        arguments["word_path"]
                    )
                
                elif name == "create_excel_from_table":
                    result = self.office_ops.create_excel_from_table(
                        arguments["table_data"],
                        arguments["excel_path"],
                        arguments.get("sheet_name", "Sheet1")
                    )
                
                elif name == "read_excel_file":
                    result = self.office_ops.read_excel_file(
                        arguments["excel_path"],
                        arguments.get("sheet_name")
                    )
                
                elif name == "create_word_document":
                    result = self.office_ops.create_word_document(
                        arguments["content"],
                        arguments["file_path"]
                    )
                
                elif name == "get_available_apps":
                    result = self.office_ops.get_available_apps()
                
                else:
                    result = {"success": False, "error": f"Unknown tool: {name}"}
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                error_result = {"success": False, "error": str(e), "traceback": traceback.format_exc()}
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    async def run(self):
        """Run the MCP server"""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            self.office_ops.cleanup()


# For backward compatibility - client class
class OfficeTool:
    """Client wrapper for Office MCP operations"""
    
    def __init__(self):
        self.office_ops = OfficeOperations()
    
    async def convert_word_to_pdf(self, word_path: str, pdf_path: str):
        return self.office_ops.convert_word_to_pdf(word_path, pdf_path)
    
    async def extract_word_tables(self, word_path: str):
        return self.office_ops.extract_word_tables(word_path)
    
    async def create_excel_from_table(self, table_data: List[List[str]], excel_path: str, sheet_name: str = "Sheet1"):
        return self.office_ops.create_excel_from_table(table_data, excel_path, sheet_name)
    
    async def read_excel_file(self, excel_path: str, sheet_name: Optional[str] = None):
        return self.office_ops.read_excel_file(excel_path, sheet_name)
    
    async def create_word_document(self, content: str, file_path: str):
        return self.office_ops.create_word_document(content, file_path)
    
    async def get_available_apps(self):
        return self.office_ops.get_available_apps()
    
    def cleanup(self):
        self.office_ops.cleanup()


async def main():
    """Main entry point for MCP server"""
    if len(sys.argv) > 1 and sys.argv[1] == "--client-test":
        # Test mode
        tool = OfficeTool()
        print("Testing Office MCP operations...")
        
        # Test available apps
        result = await tool.get_available_apps()
        print("Available apps:", json.dumps(result, indent=2))
        
        tool.cleanup()
    else:
        # MCP Server mode
        server = OfficeMCPServer()
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
