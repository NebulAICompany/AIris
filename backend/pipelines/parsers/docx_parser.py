import pythoncom
from docx2pdf import convert
from backend.pipelines.uploadpipe import UploadPipeline
from pathlib import Path

class DocxParser:
    def __init__(self, file_path: str, client=None):
        self.file_path = file_path
        self.client = client

    def run(self):
        # Initialize COM at the beginning
        pythoncom.CoInitialize()

        output_dir = Path(__file__).resolve().parent.parent / "database"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_pdf = output_dir / (Path(self.file_path).stem + ".pdf")
        convert(self.file_path, str(output_pdf))

        file_path = str(output_pdf)
        if not Path(file_path).exists():
            print(f"PDF dosyası bulunamadı: {file_path}")
            return None
        else:
            # PDF'i parse et ve text'i al
            from backend.pipelines.parsers.pdf_parser import PdfParser
            pdf_parser = PdfParser(file_path, self.client)
            extracted_text = pdf_parser.run()
            
            print("DOCX to PDF ve text extraction işlemi tamamlandı.")
            
            # Geçici PDF dosyasını sil
            try:
                Path(file_path).unlink()
            except Exception as e:
                print(f"{file_path} silinemedi: {e}")
            
            return extracted_text