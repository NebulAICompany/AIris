import openpyxl
from pathlib import Path
import openai
import base64

class ExcelParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.device = "cpu"
    
    def describe_image(self, image_bytes):
        try:
            client = openai.OpenAI(api_key="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")

            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sen uzman bir görüntü analizcisisin. Gönderilen görseli detaylı ve anlaşılır bir şekilde Türkçe olarak açıkla."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Lütfen bu görseli detaylı ve açıklayıcı bir şekilde Türkçe olarak açıkla."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=500
            )

            description = response.choices[0].message.content
            return description

        except Exception as e:
            print(f"Error in GPT image description: {e}")
            return "Açıklama alınamadı."
    
    def run(self):
        wb_obj = openpyxl.load_workbook(self.pdf_path)
        save_dir = Path(__file__).resolve().parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        pdf_stem = Path(self.pdf_path).stem
        txt_output_path = save_dir / f"{pdf_stem}_txt.txt"

        with open(txt_output_path, "w", encoding="utf-8") as f:
            for sheet in wb_obj.sheetnames:
                f.write(f"--- Sheet: {sheet} ---\n")
                worksheet = wb_obj[sheet]
                
                for row in worksheet.iter_rows():
                    for cell in row:
                        row_number = cell.row
                        col_number = cell.column
                        value = cell.value if cell.value is not None else ""
                        #if not value == "":
                            #f.write(f"[{row_number}, {col_number}] = {value}\n")
                
                 # Eğer sheet'te image varsa kontrol et
                if hasattr(worksheet, "_images") and worksheet._images:
                    f.write(f"\nSheet '{sheet}' içinde {len(worksheet._images)} resim bulundu:\n")
                    for idx, image in enumerate(worksheet._images, start=1):
                        image_bytes = image._data()  # Resmin byte datası
                        result = self.describe_image(image_bytes)
                        f.write(f"[Image ] {idx}= {result}]\n")
                f.write("\n")  # her sheet arasına boşluk bırakmak için

        print(f"Excel verisi başarıyla yazıldı.")

def main():
    #file_path = "uploads/Bilanco.xlsx"
    file_path = "uploads/TUFE.xlsx"
    #file_path = "uploads/VeriSeti.xlsx"

    parser = ExcelParser(file_path)
    parser.run()

if __name__ == "__main__":
    main()