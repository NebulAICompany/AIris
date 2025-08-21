import os
import base64
import io
import tempfile
import hashlib
import pickle
import re
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from PIL import Image
from docx2pdf import convert
import fitz

from backend.shared.logger import get_logger

logger = get_logger("PREVIEW")


class PreviewGenerator:
    """
    Generates previews for various file types including PDF, images, Excel, DOCX, and text files.
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_extension = self.file_path.suffix.lower()
        # Setup cache directory
        self.cache_dir = Path("logs/preview_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _is_temporary_file(file_path: str) -> bool:
        """
        Check if a file is a temporary file that should not be previewed.

        Common temporary file patterns:
        - ~$ prefix (Microsoft Office temporary files)
        - .tmp extension
        - .temp extension
        - .bak extension
        - .swp extension (Vim swap files)
        - .lock extension
        - Files starting with ._ (macOS hidden files)
        - Files ending with ~ (backup files)
        """
        file_name = Path(file_path).name

        # Check for common temporary file patterns
        temp_patterns = [
            r"^~\$",  # Microsoft Office temp files (like ~$document.docx)
            r"^\._",  # macOS hidden files
            r"~$",  # Backup files ending with ~
            r"\.tmp$",  # .tmp extension
            r"\.temp$",  # .temp extension
            r"\.bak$",  # .bak extension
            r"\.swp$",  # Vim swap files
            r"\.lock$",  # Lock files
            r"^\.DS_Store$",  # macOS system files
            r"^Thumbs\.db$",  # Windows thumbnail cache
            r"^desktop\.ini$",  # Windows desktop configuration
        ]

        for pattern in temp_patterns:
            if re.search(pattern, file_name, re.IGNORECASE):
                logger.info(
                    f"Skipping temporary file: {file_name} (matches pattern: {pattern})"
                )
                return True

        return False

    def _get_cache_key(self, file_path: str) -> str:
        """Generate a cache key based on file path and modification time."""
        try:
            stat = os.stat(file_path)
            # Use file path, size, and modification time for cache key
            key_data = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(key_data.encode()).hexdigest()
        except:
            # Fallback to just file path if stat fails
            return hashlib.md5(file_path.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the cache file path for a given cache key."""
        return self.cache_dir / f"{cache_key}.cache"

    def _load_from_cache(self, cache_key: str) -> Dict[str, Any]:
        """Load preview data from cache if it exists and is valid."""
        try:
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                with open(cache_path, "rb") as f:
                    cached_data = pickle.load(f)

                # Verify the cached data has the expected structure
                if (
                    isinstance(cached_data, dict)
                    and "type" in cached_data
                    and "data" in cached_data
                ):
                    logger.info(f"Using cached preview for {self.file_path.name}")
                    return cached_data
                else:
                    logger.warning(
                        f"Invalid cache data structure for {self.file_path.name}, regenerating"
                    )
            return None
        except Exception as e:
            logger.warning(f"Failed to load cache for {self.file_path.name}: {e}")
            return None

    def _save_to_cache(self, cache_key: str, preview_data: Dict[str, Any]):
        """Save preview data to cache."""
        try:
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, "wb") as f:
                pickle.dump(preview_data, f)
            logger.info(f"Preview cached for {self.file_path.name}")
        except Exception as e:
            logger.warning(f"Failed to save cache for {self.file_path.name}: {e}")

    def _clear_old_cache(self, max_cache_files: int = 100):
        """Clear old cache files if there are too many."""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            if len(cache_files) > max_cache_files:
                # Sort by modification time and remove oldest
                cache_files.sort(key=lambda x: x.stat().st_mtime)
                files_to_remove = cache_files[:-max_cache_files]
                for file_path in files_to_remove:
                    try:
                        file_path.unlink()
                        logger.info(f"Removed old cache file: {file_path.name}")
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Failed to clear old cache: {e}")

    def generate_preview(self) -> Dict[str, Any]:
        """
        Generate a preview based on the file type.
        Returns a dictionary with preview type and data.
        """
        try:
            # Check if this is a temporary file that should be skipped
            if self._is_temporary_file(str(self.file_path)):
                return {
                    "type": "error",
                    "data": "Temporary files cannot be previewed. This appears to be a temporary or lock file.",
                }

            if self.file_extension == ".pdf":
                return self._generate_pdf_preview()
            elif self.file_extension in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
                return self._generate_image_preview()
            elif self.file_extension in [".xlsx", ".xls"]:
                return self._generate_excel_preview()
            elif self.file_extension in [".docx", ".doc"]:
                return self._generate_docx_preview()
            elif self.file_extension == ".txt":
                return self._generate_text_preview()
            else:
                raise ValueError(f"Unsupported file type: {self.file_extension}")
        except Exception as e:
            return {"type": "error", "data": f"Error generating preview: {str(e)}"}

    def _generate_pdf_preview(self, temp_pdf_path: str = None) -> Dict[str, Any]:
        """Generate preview for PDF files - converts first page to image."""
        # Check cache first (only for original files, not temp files)
        if not temp_pdf_path:
            cache_key = self._get_cache_key(str(self.file_path))
            cached_preview = self._load_from_cache(cache_key)
            if cached_preview:
                return cached_preview

        # Use temp_pdf_path if provided, otherwise use the original file path
        pdf_path = temp_pdf_path if temp_pdf_path else str(self.file_path)

        pdf_document = None
        try:
            pdf_document = fitz.open(pdf_path)

            # Store page count before closing
            page_count = len(pdf_document)

            # Get the first page
            first_page = pdf_document[0]

            # Convert page to image with good quality
            mat = fitz.Matrix(2.0, 2.0)  # Scale factor for better quality
            pix = first_page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # Resize for preview (max 400px width while maintaining aspect ratio)
            img = self._resize_image_for_preview(img, max_width=400)

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            result = {
                "type": "image",
                "data": f"data:image/png;base64,{img_base64}",
                "metadata": {"pages": page_count, "title": "PDF Preview - First Page"},
            }

            # Save to cache if this is not a temp file
            if not temp_pdf_path:
                self._save_to_cache(cache_key, result)
                self._clear_old_cache()

            return result
        except Exception as e:
            return {"type": "error", "data": f"Error generating PDF preview: {str(e)}"}
        finally:
            # Ensure document is closed even if an error occurs
            if pdf_document is not None:
                try:
                    pdf_document.close()
                except:
                    pass

    def _generate_image_preview(self) -> Dict[str, Any]:
        """Generate preview for image files."""
        # Check cache first
        cache_key = self._get_cache_key(str(self.file_path))
        cached_preview = self._load_from_cache(cache_key)
        if cached_preview:
            return cached_preview

        try:
            img = Image.open(self.file_path)

            # Resize for preview
            img = self._resize_image_for_preview(img, max_width=400)

            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # Convert to base64
            buffer = io.BytesIO()
            format_type = "JPEG" if self.file_extension in [".jpg", ".jpeg"] else "PNG"
            img.save(buffer, format=format_type, quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            mime_type = f"image/{'jpeg' if format_type == 'JPEG' else 'png'}"

            result = {
                "type": "image",
                "data": f"data:{mime_type};base64,{img_base64}",
                "metadata": {
                    "format": format_type,
                    "size": f"{img.width}x{img.height}",
                },
            }

            # Save to cache
            self._save_to_cache(cache_key, result)
            self._clear_old_cache()

            return result
        except Exception as e:
            return {
                "type": "error",
                "data": f"Error generating image preview: {str(e)}",
            }

    def _generate_excel_preview(self) -> Dict[str, Any]:
        """Generate preview for Excel files - show first few rows of first sheet."""
        # Check cache first
        cache_key = self._get_cache_key(str(self.file_path))
        cached_preview = self._load_from_cache(cache_key)
        if cached_preview:
            return cached_preview

        try:
            # Read the first sheet with limited rows
            df = pd.read_excel(self.file_path, nrows=10)

            if df.empty:
                return {
                    "type": "text",
                    "data": "Excel file is empty or has no readable data.",
                }

            # Convert to HTML table for preview
            html_table = df.to_html(
                classes="excel-preview", table_id="excel-preview-table", escape=False
            )

            # Also provide text summary
            summary = f"Excel file with {len(df.columns)} columns and {len(df)} rows (showing first 10 rows)\n\n"
            summary += f"Columns: {', '.join(df.columns.astype(str))}\n\n"
            summary += df.to_string(max_rows=10, max_cols=10)

            result = {
                "type": "excel",
                "data": {
                    "html": html_table,
                    "text": summary,
                    "columns": list(df.columns.astype(str)),
                    "rows_shown": len(df),
                    "total_columns": len(df.columns),
                },
            }

            # Save to cache
            self._save_to_cache(cache_key, result)
            self._clear_old_cache()

            return result
        except Exception as e:
            return {
                "type": "error",
                "data": f"Error generating Excel preview: {str(e)}",
            }

    def _generate_docx_preview(self, max_retries: int = 2) -> Dict[str, Any]:
        """Convert DOCX with retry logic for COM errors."""
        cache_key = self._get_cache_key(str(self.file_path))
        cached_preview = self._load_from_cache(cache_key)
        if cached_preview:
            return cached_preview

        for attempt in range(max_retries + 1):
            temp_pdf = None
            try:
                # Initialize COM for Windows (fresh initialization each attempt)
                import sys

                if sys.platform.startswith("win"):
                    try:
                        import pythoncom

                        # Try to uninitialize first in case there's a stale COM state
                        try:
                            pythoncom.CoUninitialize()
                        except:
                            pass
                        # Fresh initialization
                        pythoncom.CoInitialize()
                        logger.info(
                            f"COM initialized successfully for attempt {attempt + 1}"
                        )
                    except Exception as com_error:
                        logger.error(
                            f"COM initialization failed on attempt {attempt + 1}: {com_error}"
                        )
                        if attempt == max_retries:
                            raise Exception(
                                f"COM initialization failed after {max_retries + 1} attempts"
                            )

                # Create a temporary PDF file
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf", delete=False
                ) as temp_file:
                    temp_pdf = temp_file.name

                logger.info(
                    f"Converting {self.file_path.name} to PDF (attempt {attempt + 1})"
                )

                # Convert DOCX to PDF
                convert(str(self.file_path), temp_pdf)

                # Verify the PDF was created and is not empty
                if not os.path.exists(temp_pdf) or os.path.getsize(temp_pdf) == 0:
                    raise Exception("Generated PDF is empty or doesn't exist")

                logger.info(
                    f"PDF conversion successful for {self.file_path.name} on attempt {attempt + 1}"
                )

                # Use our PDF preview logic with the temporary PDF
                result = self._generate_pdf_preview(temp_pdf)

                # Clean up the temporary PDF file after successful preview generation
                try:
                    if os.path.exists(temp_pdf):
                        os.unlink(temp_pdf)
                except:
                    pass

                # Update metadata to indicate this was from DOCX conversion
                if result.get("type") == "image" and "metadata" in result:
                    result["metadata"]["title"] = "DOCX Preview - First Page"
                    result["metadata"]["method"] = "pdf_conversion"

                # Save to cache
                self._save_to_cache(cache_key, result)
                # Clear old cache files
                self._clear_old_cache()

                return result

            except Exception as e:
                logger.error(
                    f"Conversion attempt {attempt + 1} failed for {self.file_path.name}: {e}"
                )

                # Clean up COM for this attempt
                import sys

                if sys.platform.startswith("win"):
                    try:
                        import pythoncom

                        pythoncom.CoUninitialize()
                    except:
                        pass

                # Clean up temporary PDF file
                if temp_pdf and os.path.exists(temp_pdf):
                    try:
                        os.unlink(temp_pdf)
                    except:
                        pass

                # If this was the last attempt, raise the exception
                if attempt == max_retries:
                    raise e

                # Wait a bit before retrying
                import time

                time.sleep(0.5)

        # This should never be reached, but just in case
        raise Exception("Unexpected error in conversion retry logic")

    def _generate_text_preview(self) -> Dict[str, Any]:
        """Generate preview for text files - show first few lines."""
        # Check cache first
        cache_key = self._get_cache_key(str(self.file_path))
        cached_preview = self._load_from_cache(cache_key)
        if cached_preview:
            return cached_preview

        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                lines = []
                for i, line in enumerate(file):
                    if i >= 20:  # Limit to first 20 lines
                        break
                    lines.append(line.rstrip())

                preview_text = "\n".join(lines)

                # Limit total length
                if len(preview_text) > 500:
                    preview_text = preview_text[:500] + "..."

                result = {
                    "type": "text",
                    "data": preview_text,
                    "metadata": {"lines_shown": len(lines), "encoding": "utf-8"},
                }

                # Save to cache
                self._save_to_cache(cache_key, result)
                self._clear_old_cache()

                return result
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(self.file_path, "r", encoding="latin-1") as file:
                    content = file.read(500)
                    result = {
                        "type": "text",
                        "data": content + ("..." if len(content) == 500 else ""),
                        "metadata": {"encoding": "latin-1"},
                    }

                    # Save to cache
                    self._save_to_cache(cache_key, result)
                    self._clear_old_cache()

                    return result
            except Exception as e:
                return {"type": "error", "data": f"Error reading text file: {str(e)}"}
        except Exception as e:
            return {"type": "error", "data": f"Error generating text preview: {str(e)}"}

    def _resize_image_for_preview(
        self, img: Image.Image, max_width: int = 400
    ) -> Image.Image:
        """Resize image for preview while maintaining aspect ratio."""
        if img.width <= max_width:
            return img

        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        return img.resize((max_width, new_height), Image.Resampling.LANCZOS)
