import openai, pythoncom, os
from docx2pdf import convert


class DocxParser:
    def __init__(self, file_path: str, txt_output_path: str):
        self.file_path = file_path
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.txt_output_path = txt_output_path

    def run(self):
        from backend.pipelines.uploadpipe import UploadPipeline
        from pathlib import Path

        # Initialize COM at the beginning
        pythoncom.CoInitialize()

        import json
        with open("paths.json", "r") as f:
            paths = json.load(f)
        output_dir = Path(paths["UPLOADS_PATH"])
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