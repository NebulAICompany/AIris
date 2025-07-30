import os
import sys
from pathlib import Path

# Add the project root to system path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from backend.pipelines.uploadpipe import UploadPipeline
import backend.pipelines.vectorpipe as vectorpipe

# Vector store path
VECTOR_STORE_PATH = "backend/vectorstore"


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

    _, ext = os.path.splitext(file_path)

    try:
        # Step 1: Create UploadPipeline
        pipeline = UploadPipeline(file_path=file_path)

        pipeline.run()
        save_dir = Path(__file__).resolve().parent.parent / "database"

        # Step 2: Determine the expected output filename
        # All parsers follow the pattern: original_stem + "_txt.txt"
        original_stem = Path(file_path).stem
        expected_output_filename = f"{original_stem}_txt.txt"

        # Step 3: Create or update vector store with the specific file
        from backend.pipelines.vectorpipe import PreEmbeddingProcess

        # Convert string to enum
        if pre_embedding_process.lower() == "hype":
            process_enum = PreEmbeddingProcess.HYPE
        elif pre_embedding_process.lower() == "cch":
            process_enum = PreEmbeddingProcess.CCH
        else:
            process_enum = PreEmbeddingProcess.NONE

        vectorpipe.VectorStorePipeline(pre_embedding_process=process_enum).run(
            uploads_path=save_dir,
            save_path=VECTOR_STORE_PATH,
            specific_file=expected_output_filename,
        )

        return {
            "status": "success",
            "message": "File processed successfully",
            "vector_store_path": VECTOR_STORE_PATH,
        }
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise e
