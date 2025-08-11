import os
from pathlib import Path
import backend.pipeline.vector as vectorpipe
from backend.shared.logger import get_logger
from backend.shared.constants import VECTORSTORE_PATH_STR
from backend.utils.parser import AzureParser, TxtParser, ImageParser
from backend.pipeline.vector import PreEmbeddingProcess

logger = get_logger("UPLOAD")
async def process_file(file_path: str, pre_embedding_process: str = "none") -> dict:
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
        file_extension = Path(file_path).suffix.lower()

        extracted_text = ""
        if file_extension in ('.pdf', '.docx', '.xlsx'):
            extracted_text = await AzureParser(file_path)
        elif file_extension == '.txt':
            extracted_text = await TxtParser(file_path)
        elif file_extension in ('.jpg', '.jpeg', '.gif', '.bmp', '.png'):
            extracted_text = await ImageParser(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Step 2: Create or update vector store directly with the extracted text

        # Convert string to enum
        if pre_embedding_process.lower() == "cch":
            process_enum = PreEmbeddingProcess.CCH
        elif pre_embedding_process.lower() == "pdr":
            process_enum = PreEmbeddingProcess.PDR
        else:
            process_enum = PreEmbeddingProcess.NONE
        logger.info(f"Pre-embedding process: {process_enum}")
        original_stem = Path(file_path).stem

        vectorpipe.VectorStorePipeline(pre_embedding_process=process_enum).run(
            text_content=extracted_text,
            document_name=original_stem,
        )

        return {
            "status": "success",
            "message": "File processed successfully",
            "vector_store_path": VECTORSTORE_PATH_STR,
        }
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise e