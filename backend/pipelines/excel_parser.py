import openpyxl, openai, os
from backend.pipelines.tools import describe_image, describe_chart

class ExcelParser:
    def __init__(self, file_path: str, txt_output_path: str):
        self.file_path = file_path
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.txt_output_path = txt_output_path
    
    def run(self):
        wb_obj = openpyxl.load_workbook(self.file_path)
        
        with open(self.txt_output_path, "w", encoding="utf-8") as f:
            for sheet in wb_obj.sheetnames:
                f.write(f"--- Sheet: {sheet} ---\n")
                worksheet = wb_obj[sheet]

                # Eğer bu bir normal worksheet ise
                if isinstance(worksheet, openpyxl.worksheet.worksheet.Worksheet):
                    for row in worksheet.iter_rows():
                        for cell in row:
                            value = cell.value if cell.value is not None else ""
                            if not value == "":
                                f.write(f"[{cell.row}, {cell.column}] = {value}\n")

                # Eğer sheet'te image varsa kontrol et
                if hasattr(worksheet, "_images") and worksheet._images:
                    for idx, image in enumerate(worksheet._images, start=1):
                        image_bytes = image._data()  # Resmin byte datası
                        result = describe_image(image_bytes)
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

                        description = describe_chart(chart_data)
                        f.write(f"\n[Description] =\n {description}\n")
                        f.write("---\n")
                f.write("\n")  # her sheet arasına boşluk bırakmak için
        print(f"Excel verisi başarıyla yazıldı.")
