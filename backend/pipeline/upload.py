import os
from pathlib import Path
import backend.pipeline.vector as vectorpipe
from backend.security.pii import mask_text
from backend.shared.logger import get_logger
from backend.shared.constants import VECTORSTORE_PATH_STR
from backend.utils.parser import AzureParser, TxtParser, ImageParser
from backend.pipeline.vector import PreEmbeddingProcess
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

        batches = RecursiveCharacterTextSplitter(
            chunk_size=4500,
            chunk_overlap=200,
            length_function=len,
        ).split_text(extracted_text)

        # Batch'leri 10'lu gruplar halinde PII maskeleme işleminden geçir
        masked_batches = []
        batch_size = 20

        for i in range(0, len(batches), batch_size):
            batch_group = batches[i:i + batch_size]
            logger.info(f"Processing batch group {i//batch_size + 1}/{(len(batches) + batch_size - 1)//batch_size} ({len(batch_group)} batches)")

            masked_group = await mask_text(batch_group, f"batch_group_{i//batch_size + 1}")
            masked_batches.extend(masked_group)

        logger.info(f"PII masking completed for all {len(batches)} batches in {(len(batches) + batch_size - 1)//batch_size} groups")

        # Maskelenmiş batch'leri birleştir
        masked_text = " ".join(masked_batches)
        logger.info(f"PII masking completed for all {len(batches)} batches")
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
            text_content=masked_text,
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