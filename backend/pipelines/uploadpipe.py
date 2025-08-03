from pathlib import Path
import os, logging, warnings
from backend.shared.constants import openai_client

logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


class UploadPipeline:
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def run(self):

        from backend.pipelines.parsers.docx_parser import DocxParser
        from backend.pipelines.parsers.excel_parser import ExcelParser
        from backend.pipelines.parsers.pdf_parser import PdfParser
        from backend.pipelines.parsers.txt_parser import TxtParser
        from backend.pipelines.parsers.image_parser import ImageParser
        
        file_extension = Path(self.file_path).suffix.lower()

        if file_extension == '.pdf':
            parser = PdfParser(self.file_path)
        elif file_extension == '.docx':
            parser = DocxParser(self.file_path)
        elif file_extension in ('.xlsx', '.xls'):
            parser = ExcelParser(self.file_path)
        elif file_extension == '.txt':
            parser = TxtParser(self.file_path)
        elif file_extension in ('.jpg', '.jpeg', '.gif', '.bmp', '.png'):
            parser = ImageParser(self.file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        extracted_text = parser.run()
        print(f"File processed successfully. Text length: {len(extracted_text)} characters")
        return extracted_text
        