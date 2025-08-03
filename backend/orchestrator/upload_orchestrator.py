import os
import sys
from pathlib import Path
import backend.pipelines.vectorpipe as vectorpipe
import json
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

with open("paths.json", "r") as f:
    paths = json.load(f)
VECTOR_STORE_PATH = paths["VECTORSTORE_PATH"]

def process_file(file_path: str, pre_embedding_process: str = "none") -> dict:
    """
    Process an uploaded file synchronously.
    Args:
        file_path: Path to the uploaded file
    Returns:
        Dictionary with processing results
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Uploaded file not found: {file_path}")

    try:
        # Step 1: Create UploadPipeline and get extracted text
        # pipeline = UploadPipeline(file_path=file_path)
        # extracted_text = pipeline.run()

        from backend.pipelines.parsers.pdf_parser import PdfParser
        from backend.pipelines.parsers.parser_set import TxtParser, ImageParser, ExcelParser, DocxParser 
  
        file_extension = Path(file_path).suffix.lower()

        if file_extension == '.pdf':
            parser = PdfParser(file_path)
        elif file_extension == '.docx':
            parser = DocxParser(file_path)
        elif file_extension in ('.xlsx', '.xls'):
            parser = ExcelParser(file_path)
        elif file_extension == '.txt':
            parser = TxtParser(file_path)
        elif file_extension in ('.jpg', '.jpeg', '.gif', '.bmp', '.png'):
            parser = ImageParser(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        extracted_text = parser.run()

        # Step 2: Create or update vector store directly with the extracted text
        from backend.pipelines.vectorpipe import PreEmbeddingProcess

        # Convert string to enum
        if pre_embedding_process.lower() == "hype":
            process_enum = PreEmbeddingProcess.HYPE
        elif pre_embedding_process.lower() == "cch":
            process_enum = PreEmbeddingProcess.CCH
        else:
            process_enum = PreEmbeddingProcess.NONE

        # Get original filename for reference
        original_stem = Path(file_path).stem

        vectorpipe.VectorStorePipeline(pre_embedding_process=process_enum).run(
            text_content=extracted_text,
            document_name=original_stem,
            vectorstore_path=VECTOR_STORE_PATH,
        )

        return {
            "status": "success",
            "message": "File processed successfully",
            "vector_store_path": VECTOR_STORE_PATH,
        }
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise e