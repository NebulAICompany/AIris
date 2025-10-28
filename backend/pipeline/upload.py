import os
from pathlib import Path
import backend.pipeline.vector as vectorpipe
from backend.shared.logger import get_logger
from backend.utils.parser import AzureParser, TxtParser, ImageParser
from backend.pipeline.vector import PreEmbeddingProcess
import pandas as pd
from backend.shared.constants import UPLOADS_PATH
from backend.utils.uploads_database import uploads_db

logger = get_logger("UPLOAD")


async def parse_document(file_path: str) -> str:
    """
    Parse document and extract text based on file type.
    Args:
        file_path: Path to the file to parse
    Returns:
        Extracted text content
    """
    try:
        file_extension = Path(file_path).suffix.lower()
        if file_extension in (".pdf", ".docx", ".xlsx"):
            extracted_text = await AzureParser(file_path)
        elif file_extension == ".txt":
            extracted_text = await TxtParser(file_path)
        elif file_extension in (".jpg", ".jpeg", ".gif", ".bmp", ".png"):
            extracted_text = await ImageParser(file_path)
        elif file_extension == ".xls":
            # Read the old .xls and create a new file in .xlsx format
            df = pd.read_excel(file_path)
            new_file_path = Path(UPLOADS_PATH) / f"{Path(file_path).stem}.xlsx"
            df.to_excel(str(new_file_path), index=False)
            logger.info(f"Converted {file_path} to {new_file_path}")
            # Parse the new xlsx file
            extracted_text = await AzureParser(str(new_file_path))
            # Delete the temporary xlsx file after processing
            if os.path.exists(new_file_path):
                os.remove(new_file_path)
                logger.info(f"Deleted temporary file: {new_file_path}")
        elif file_extension == ".doc":
            # Convert .doc to .docx format using an external library
            from win32com import client as wc

            # Create a temporary .docx file path
            new_file_path = Path(UPLOADS_PATH) / f"{Path(file_path).stem}.docx"

            # Use win32com to convert .doc to .docx
            try:
                word = wc.Dispatch("Word.Application")
                doc = word.Documents.Open(file_path)
                doc.SaveAs(
                    str(new_file_path), 16
                )  # 16 represents the value for .docx format
                doc.Close()
                word.Quit()
                logger.info(f"Converted {file_path} to {new_file_path}")

                # Parse the new docx file
                extracted_text = await AzureParser(str(new_file_path))

                # Delete the temporary docx file after processing
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
                    logger.info(f"Deleted temporary file: {new_file_path}")
            except Exception as e:
                logger.error(f"Error converting .doc to .docx: {str(e)}")
                raise e
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        return extracted_text if extracted_text else ""

    except Exception as e:
        logger.error(f"Document parsing failed: {str(e)}")
        raise e


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
        # Parse document using the new method
        extracted_text = await parse_document(file_path)

        # Convert string to enum
        if pre_embedding_process.lower() == "cch":
            process_enum = PreEmbeddingProcess.CCH
        else:
            process_enum = PreEmbeddingProcess.NONE
        logger.info(f"Pre-embedding process: {process_enum}")
        original_stem = Path(file_path).stem

        await vectorpipe.VectorStorePipeline(pre_embedding_process=process_enum).run(
            text_content=extracted_text,
            document_name=original_stem,
        )

        # Record the upload in the database
        try:
            file_extension = Path(file_path).suffix.lower()
            uploads_db.add_upload_record(
                file_name=original_stem, file_type=file_extension
            )
        except Exception as e:
            # Log error but don't fail the upload if tracking fails
            logger.warning(f"Failed to record upload in database: {str(e)}")

        return {
            "status": "success",
            "message": "File processed successfully",
            "file_name": original_stem,
            "text_length": len(extracted_text),
        }

    except Exception as e:
        logger.error(f"File processing failed: {str(e)}")
        return {
            "status": "error",
            "message": f"File processing failed: {str(e)}",
            "file_name": Path(file_path).name,
        }
