from pathlib import Path
import openai
import pythoncom
import os
from docx2pdf import convert


class DocxParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run(self):
        from aiiris_backend.pipelines.uploadpipe import UploadPipeline
        from pathlib import Path

        # Initialize COM at the beginning
        pythoncom.CoInitialize()

        output_dir = Path(__file__).resolve().parent / "uploads"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_pdf = output_dir / (Path(self.file_path).stem + ".pdf")
        self.convert_docx_to_pdf(self.file_path, str(output_pdf))

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

    def convert_docx_to_pdf(self, input_path, output_dir):
        convert(input_path, output_dir)
