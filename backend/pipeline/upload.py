import os
from pathlib import Path
import backend.pipeline.vector as vectorpipe
from backend.shared.constants import VECTORSTORE_PATH
from backend.shared.logger import get_logger
logger = get_logger("UPLOAD")
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
        # Step 1: Call parser and get extracted text
        from backend.utils.parser import TxtParser, ImageParser, ExcelParser, DocxParser, PdfParser
  
        file_extension = Path(file_path).suffix.lower()

        extracted_text = ""
        if file_extension == '.pdf':
            extracted_text = PdfParser(file_path)
        elif file_extension == '.docx':
            extracted_text = DocxParser(file_path)
        elif file_extension in ('.xlsx', '.xls'):
            extracted_text = ExcelParser(file_path)
        elif file_extension == '.txt':
            extracted_text = TxtParser(file_path)
        elif file_extension in ('.jpg', '.jpeg', '.gif', '.bmp', '.png'):
            extracted_text = ImageParser(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Step 2: Create or update vector store directly with the extracted text
        from backend.pipeline.vector import PreEmbeddingProcess

        # Convert string to enum
        if pre_embedding_process.lower() == "cch":
            process_enum = PreEmbeddingProcess.CCH
        else:
            process_enum = PreEmbeddingProcess.NONE

        # Get original filename for reference
        original_stem = Path(file_path).stem

        vectorpipe.VectorStorePipeline(pre_embedding_process=process_enum).run(
            text_content=extracted_text,
            document_name=original_stem,
            save_path=VECTORSTORE_PATH,
        )

        return {
            "status": "success",
            "message": "File processed successfully",
            "vector_store_path": VECTORSTORE_PATH,
        }
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise e