from PIL import Image
import io
from pathlib import Path
import openpyxl
from backend.pipelines.parsers.tools import describe_image, describe_chart, specify_sentence

class ExcelParser:
    def __init__(self, file_path: str, txt_output_path: str, client=None):
        self.file_path = file_path
        self.client = client
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
                    images_dir = Path("images")
                    images_dir.mkdir(exist_ok=True)
                    for idx, image in enumerate(worksheet._images, start=1):
                        image_bytes = image._data()  # Resmin byte datası
                        
                        # Kaydet
                        image_filename = f"{self.file_path.stem}_{sheet}_image_{idx}.png"
                        image_path = images_dir / image_filename
                        
                        # Görseli kaydet
                        img = Image.open(io.BytesIO(image_bytes))
                        img.save(image_path)

                        # Image reference için sadece dosya adını kullan (uzantısız)
                        image_reference = f"{self.file_path.stem}_{sheet}_image_{idx}"
                        result = describe_image(image_bytes)
                        updated_description = specify_sentence(result, f"((Image):{image_reference})")
                        f.write(f"[Image {idx}]\n[Description] = {updated_description}\n")

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
