import base64
from pathlib import Path
import openai
import os


class ImageParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run(self):
        if not Path(self.file_path).exists():
            print(f"Görsel dosyası bulunamadı: {self.file_path}")
            return None

        with open(self.file_path, "rb") as f:
            image_bytes = f.read()

        save_dir = Path(__file__).resolve().parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        file_stem = Path(self.file_path).stem
        txt_output_path = save_dir / f"{file_stem}_txt.txt"

        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(f"Görsel dosyası: {self.file_path}\n")
            f.write("Açıklama:\n")
            description = self.describe_image(image_bytes)
            f.write(description + "\n")

        print(f"Açıklama {txt_output_path} dosyasına kaydedildi.")

    def describe_image(self, image_bytes):
        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            image_mime_type = self.get_mime_type()

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen uzman bir görüntü analizcisisin. Gönderilen görseli grafik mi fotoğraf mı olduğunu belirle. Fotoğrafsa neyi gösterdiğini kısaca söyle, grafikse oldukça detaylı biçimde finans konseptiyle açıkla.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Lütfen bu görseli inceleyip önce türünü belirt, grafikse türünü ve detaylı açıklamasını yap.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime_type};base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
                max_tokens=1000,
            )

            description = response.choices[0].message.content
            return description

        except Exception as e:
            print(f"Error in GPT image description: {e}")
            return "Açıklama alınamadı."

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
