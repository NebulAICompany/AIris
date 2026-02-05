import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from backend.shared.logger import get_logger
from backend.shared.constants import UPLOADS_DB_PATH

logger = get_logger("UPLOADS_DATABASE")


class UploadsDatabase:
    """Manages SQLite database for uploaded files tracking"""

    def __init__(self, db_path: Path = UPLOADS_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize database with uploaded_files table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS uploaded_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_name TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        document_date TEXT
                    )
                """
                )

                # Add document_date column if it doesn't exist (migration)
                try:
                    conn.execute("ALTER TABLE uploaded_files ADD COLUMN document_date TEXT")
                except sqlite3.OperationalError:
                    pass  # Column already exists

                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_file_name ON uploaded_files(file_name)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_upload_date ON uploaded_files(upload_date DESC)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_document_date ON uploaded_files(document_date)"
                )

                conn.commit()
                logger.info("✅ Uploads database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Uploads database initialization failed: {e}")
            raise

    def add_upload_record(self, file_name: str, file_type: str, document_date: str = None) -> bool:
        """
        Add a new upload record to the database.

        Args:
            file_name: Name of the uploaded file
            file_type: File extension/type (e.g., '.pdf', '.docx')
            document_date: Extracted document date (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO uploaded_files (file_name, file_type, document_date) VALUES (?, ?, ?)",
                    (file_name, file_type, document_date),
                )
                conn.commit()
                logger.info(f"✅ Upload record added: {file_name} ({file_type}) date: {document_date}")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to add upload record for {file_name}: {e}")
            return False

    def get_all_uploads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve all upload records, ordered by most recent first.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """SELECT id, file_name, file_type, upload_date, document_date
                    FROM uploaded_files ORDER BY upload_date DESC LIMIT ?""",
                    (limit,),
                )

                return [
                    {
                        "id": row["id"],
                        "file_name": row["file_name"],
                        "file_type": row["file_type"],
                        "upload_date": row["upload_date"],
                        "document_date": row["document_date"],
                    }
                    for row in cursor
                ]

        except Exception as e:
            logger.error(f"❌ Failed to retrieve uploads: {e}")
            return []

    def count_uploads(self) -> int:
        """
        Get total count of uploaded files.

        Returns:
            Total number of uploaded files
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) as count FROM uploaded_files
                """
                )
                result = cursor.fetchone()
                return result[0] if result else 0

        except Exception as e:
            logger.error(f"❌ Failed to count uploads: {e}")
            return 0

    def count_by_file_type(self) -> Dict[str, int]:
        """
        Get count of uploads grouped by file type.

        Returns:
            Dictionary with file types as keys and counts as values
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT file_type, COUNT(*) as count
                    FROM uploaded_files
                    GROUP BY file_type
                    ORDER BY count DESC
                """
                )

                results = {}
                for row in cursor:
                    results[row["file_type"]] = row["count"]

                return results

        except Exception as e:
            logger.error(f"❌ Failed to count uploads by file type: {e}")
            return {}

    def delete_upload_record(self, file_name: str) -> bool:
        """
        Delete an upload record from the database by file name.

        Args:
            file_name: Name of the file to delete (with or without extension)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remove extension if present for matching
                base_name = Path(file_name).stem
                
                cursor = conn.execute(
                    "DELETE FROM uploaded_files WHERE file_name = ?",
                    (base_name,),
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"✅ Upload record deleted: {base_name}")
                    return True
                else:
                    logger.warning(f"⚠️ No upload record found to delete: {base_name}")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to delete upload record for {file_name}: {e}")
            return False


# Create a singleton instance
uploads_db = UploadsDatabase()
