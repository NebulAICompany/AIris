import openpyxl
from pathlib import Path
import openai
import base64
import os


class ExcelParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run(self):
        wb_obj = openpyxl.load_workbook(self.file_path)
        save_dir = Path(__file__).resolve().parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        pdf_stem = Path(self.file_path).stem
        txt_output_path = save_dir / f"{pdf_stem}_txt.txt"

        with open(txt_output_path, "w", encoding="utf-8") as f:
            for sheet in wb_obj.sheetnames:
                f.write(f"--- Sheet: {sheet} ---\n")
                worksheet = wb_obj[sheet]

                # Eğer bu bir normal worksheet ise
                if isinstance(worksheet, openpyxl.worksheet.worksheet.Worksheet):
                    for row in worksheet.iter_rows():
                        for cell in row:
                            row_number = cell.row
                            col_number = cell.column
                            value = cell.value if cell.value is not None else ""
                            if not value == "":
                                f.write(f"[{row_number}, {col_number}] = {value}\n")

                # Eğer sheet'te image varsa kontrol et
                if hasattr(worksheet, "_images") and worksheet._images:
                    for idx, image in enumerate(worksheet._images, start=1):
                        image_bytes = image._data()  # Resmin byte datası
                        result = self.describe_image(image_bytes)
                        f.write(f"[Image {idx}]\n[Description] = {result}\n")

                if hasattr(worksheet, "_charts") and worksheet._charts:
                    for idx, chart in enumerate(worksheet._charts, start=1):
                        chart_data = []

                        f.write(f"[Chart {idx}] = {chart.title}\n")
                        f.write(f"Chart type: {type(chart).__name__}\n")
                        chart_data.append(f"[Chart {idx}] = {chart.title}\n")
                        f.write(f"\nChart data\n")

                        for s in chart.series:

                            f.write(f"Seri adı: {s.title.strRef.strCache.pt[0].v}\n")
                            chart_data.append(
                                f"Seri adı: {s.title.strRef.strCache.pt[0].v}\n"
                            )
                            # Değerler
                            values = []
                            if hasattr(s, "values"):
                                # Bazı eski openpyxl sürümlerinde olabilir
                                values = [v.value for v in s.values]
                            elif (
                                hasattr(s, "val")
                                and hasattr(s.val, "numRef")
                                and hasattr(s.val.numRef, "numCache")
                            ):
                                num_cache = s.val.numRef.numCache
                                values = [p.v for p in getattr(num_cache, "pt", [])]
                            if values:
                                f.write(f"Değerler: {values}\n")
                                chart_data.append(f"Değerler: {values}\n")
                            # Kategoriler
                            categories = []
                            if hasattr(s, "categories"):
                                categories = [c.value for c in s.categories]
                            elif (
                                hasattr(s, "cat")
                                and hasattr(s.cat, "strRef")
                                and hasattr(s.cat.strRef, "strCache")
                            ):
                                str_cache = s.cat.strRef.strCache
                                categories = [p.v for p in getattr(str_cache, "pt", [])]
                            if categories:
                                f.write(f"\nKategoriler: {categories}\n")
                                chart_data.append(f"Kategoriler: {categories}\n")
                            f.write("\n")

                        description = self.describe_chart(chart_data)
                        f.write(f"\n[Description] =\n {description}\n")
                        f.write("---\n")
                f.write("\n")  # her sheet arasına boşluk bırakmak için
        print(f"Excel verisi başarıyla yazıldı.")

    def describe_chart(self, chart_data):
        """
        Grafik verilerini GPT-4'e göndererek Türkçe açıklama üretir.
        Args:chart_data (list): Grafikle ilgili verilerin listesi (başlık, seri adları, değerler, kategoriler)
        Returns:str: GPT tarafından oluşturulan Türkçe grafik açıklaması
        """
        try:
            # Grafik verilerini metin formatında birleştir
            chart_text = "\n".join(chart_data)
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Sen bir veri analizi uzmanısın. Aşağıda verilen grafik bilgilerini analiz edip "
                            "anlaşılır ve detaylı bir Türkçe özet oluştur. Grafiğin türünü, gösterdiği verileri, "
                            "eğilimleri ve dikkat çeken noktaları açıkla. Grafik başlığına özellikle dikkat et."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Bu grafik verilerini analiz edip Türkçe açıklama yapar mısın?\n\n{chart_text}",
                    },
                ],
                max_tokens=2000,
                temperature=0.7,
            )
            description = response.choices[0].message.content
            return description
        except Exception as e:
            print(f"Error in GPT chart description: {e}")
            return "Grafik açıklaması alınamadı."

    def describe_image(self, image_bytes):
        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen uzman bir görüntü analizcisisin. Gönderilen görseli detaylı ve anlaşılır bir şekilde Türkçe olarak açıkla.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Lütfen bu görseli detaylı ve açıklayıcı bir şekilde Türkçe olarak açıkla.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
                max_tokens=700,
            )
            description = response.choices[0].message.content
            return description

        except Exception as e:
            print(f"Error in GPT image description: {e}")
            return "Açıklama alınamadı."
