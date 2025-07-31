import pythoncom
from docx2pdf import convert
from backend.pipelines.uploadpipe import UploadPipeline
from pathlib import Path

class DocxParser:
    def __init__(self, file_path: str, txt_output_path: str, client=None):
        self.file_path = file_path
        self.client = client
        self.txt_output_path = txt_output_path

    def run(self):
        # Initialize COM at the beginning
        pythoncom.CoInitialize()

        output_dir = Path(__file__).resolve().parent / "database"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_pdf = output_dir / (Path(self.file_path).stem + ".pdf")
        convert(self.file_path, str(output_pdf))

        file_path = str(output_pdf)
        if not Path(file_path).exists():
            print(f"PDF dosyası bulunamadı: {file_path}")
            return None
        else:
            pipe = UploadPipeline(file_path)
            pipe.run()
            print("DOCX to PDF ve UploadPipeline işlemi tamamlandı.")
            try:
                Path(file_path).unlink()
            except Exception as e:
                print(f"{file_path} silinemedi: {e}")