from pathlib import Path
import openai, os
from backend.pipelines.tools import describe_image

class ImageParser:
    def __init__(self, file_path: str, txt_output_path: str):
        self.file_path = file_path
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.txt_output_path = txt_output_path

    def run(self):
        if not Path(self.file_path).exists():
            print(f"Görsel dosyası bulunamadı: {self.file_path}")
            return None

        with open(self.file_path, "rb") as f:
            image_bytes = f.read()

        with open(self.txt_output_path, "w", encoding="utf-8") as f:
            f.write(f"Görsel dosyası: {self.file_path}\n")
            f.write("Açıklama:\n")
            description = describe_image(image_bytes)
            f.write(description + "\n")

        print(f"Açıklama {self.txt_output_path} dosyasına kaydedildi.")


    def get_mime_type(self):
        extension = Path(self.file_path).suffix.lower()
        if extension == ".png":
            return "image/png"
        elif extension in [".jpg", ".jpeg"]:
            return "image/jpeg"
        elif extension == ".gif":
            return "image/gif"
        elif extension == ".bmp":
            return "image/bmp"
        else:
            return "application/octet-stream"  # bilinmeyen format
