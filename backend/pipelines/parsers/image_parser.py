from pathlib import Path
from PIL import Image
import io
from backend.pipelines.parsers.tools import describe_image, specify_sentence

class ImageParser:
    def __init__(self, file_path: str, txt_output_path: str, client=None):
        self.file_path = file_path
        self.client = client
        self.txt_output_path = txt_output_path

    def run(self):
        image_path = Path(self.file_path)
        if not image_path.exists():
            print(f"Görsel dosyası bulunamadı: {self.file_path}")
            return None

        with open(self.file_path, "rb") as f:
            image_bytes = f.read()

        # Görseli aç (PIL kullanarak)
        image = Image.open(io.BytesIO(image_bytes))

        # images/ klasörü oluşturulmamışsa oluştur
        images_dir = Path(__file__).parent.parent / "images"
        images_dir.mkdir(exist_ok=True)

        # Görseli kaydet
        saved_image_path = images_dir / Path(self.file_name).stem
        image.save(saved_image_path)

        # Açıklamayı al
        description = describe_image(image_bytes, client=self.client)
        updated_description = specify_sentence(description, f"((Image):{Path(self.file_name).stem})")

        # Açıklama dosyasına yaz
        with open(self.txt_output_path, "w", encoding="utf-8") as f:
            f.write("Açıklama:\n")
            f.write(updated_description + "\n")

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
