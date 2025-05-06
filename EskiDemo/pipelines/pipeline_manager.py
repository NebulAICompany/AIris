from typing import List, Optional
import os
from pathlib import Path
import sys
import threading
from queue import Queue
import time

os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
    "https://airis.cognitiveservices.azure.com/"
)
os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "a2302a791af84047a664bc16174435cb"


class PipelineManager:
    def __init__(self):
        # Göreceli yollar kullan - proje ana dizininden başlayacak şekilde
        self.base_dir = Path(__file__).resolve().parent.parent
        self.uploads_dir = self.base_dir / "uploads"  # Corrected path
        self.vectorstore_dir = self.base_dir / "vectorstore"  # Corrected path
        self.message_queue = Queue()
        self.callback_queue = Queue()
        self.processing_lock = threading.Lock()
        self.processed_files = []

        # Check for Azure credentials in environment variables
        self.azure_endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.azure_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        # Create necessary directories
        self.uploads_dir.mkdir(exist_ok=True)
        self.vectorstore_dir.mkdir(exist_ok=True)

        # Import pipelines dynamically to avoid circular imports
        sys.path.append(str(Path(__file__).parent))
        from pipelines.upload_pipeline import UploadPipeline, VectorStorePipeline
        from pipelines.query_pipeline import QueryPipeline

        self.UploadPipeline = UploadPipeline
        self.VectorStorePipeline = VectorStorePipeline
        self.QueryPipeline = QueryPipeline

    def process_file(self, file_path: str, progress_callback=None) -> bool:
        """Process a single file through the upload pipeline"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Create upload pipeline instance with Azure credentials
            upload_pipeline = self.UploadPipeline(
                file_path, azure_endpoint=self.azure_endpoint, azure_key=self.azure_key
            )

            # Extract text
            extracted_text = upload_pipeline.run()

            # Save extracted text
            upload_pipeline.save(extracted_text, str(self.uploads_dir))

            if progress_callback:
                progress_callback(f"Processed {Path(file_path).name}")

            with self.processing_lock:
                self.processed_files.append(file_path)

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"Error processing {Path(file_path).name}: {str(e)}")
            return False

    def update_vectorstore(self, progress_callback=None) -> bool:
        """Update vector store with processed files"""
        try:
            with self.processing_lock:
                if not self.processed_files:
                    if progress_callback:
                        progress_callback("No new files to update in vector store")
                    return True

            # Create vector store pipeline instance
            vector_store = self.VectorStorePipeline()

            # Update vector store
            vector_store.run(str(self.uploads_dir), str(self.vectorstore_dir))

            if progress_callback:
                progress_callback("Vector store updated successfully")

            with self.processing_lock:
                self.processed_files.clear()

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"Error updating vector store: {str(e)}")
            return False

    def query_documents(self, query: str) -> str:
        """Query the vector store and return response"""
        try:
            if not os.path.exists(self.vectorstore_dir):  # Updated path
                return "Error: Vector store not found. Please upload documents first."

            # Create query pipeline instance
            query_pipeline = self.QueryPipeline(
                query=query, vectorstore_path=str(self.vectorstore_dir)
            )

            # Generate response
            response = query_pipeline.generate_response()

            return response

        except Exception as e:
            return f"Error generating response: {str(e)}"

    def process_files_async(self, files: List[str], callback) -> None:
        """Process multiple files asynchronously, skipping already processed files"""

        # Identify files that have not been processed yet
        new_files = [file for file in files if file not in self.processed_files]

        if not new_files:
            callback("All selected files have already been processed.")
            return

        def process_worker():
            while not self.message_queue.empty():
                try:
                    file_path = self.message_queue.get_nowait()
                    if file_path in self.processed_files:
                        callback(
                            f"Skipping already processed file: {Path(file_path).name}"
                        )
                    else:
                        success = self.process_file(file_path, callback)
                        if success:
                            with self.processing_lock:
                                self.processed_files.append(file_path)
                        self.callback_queue.put(success)
                    self.message_queue.task_done()
                except Exception:
                    break

            # Update vector store after all new files are processed
            self.update_vectorstore(callback)

        # Add only new files to queue
        for file_path in new_files:
            self.message_queue.put(file_path)

        # Start worker thread
        thread = threading.Thread(target=process_worker)
        thread.daemon = True
        thread.start()
