from pathlib import Path
import os
import logging
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

from aiiris_backend.pipelines.docx_parser import DocxParser
from aiiris_backend.pipelines.excel_parser import ExcelParser
from aiiris_backend.pipelines.pdf_parser import PdfParser
from aiiris_backend.pipelines.txt_parser import TxtParser
from aiiris_backend.pipelines.image_parser import ImageParser
import traceback

class UploadPipeline:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.device = "cpu"
    
    def run(self):
        file_extension = Path(self.file_path).suffix.lower()
        
        if file_extension == '.pdf':
            parser = PdfParser(self.file_path)
        elif file_extension == '.docx':
            parser = DocxParser(self.file_path)
        elif file_extension in ('.xlsx', '.xls'):
            parser = ExcelParser(self.file_path)
        elif file_extension == '.txt':
            parser = TxtParser(self.file_path)
        elif file_extension in ('.jpg', '.jpeg', '.gif', '.bmp', '.png'):
            parser = ImageParser(self.file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        return parser.run()
        
def main():
    #file_path = "aiiris_backend/files/pdf_file.pdf"
    #file_path = "aiiris_backend/files/market_demand.pdf"
    #file_path = "aiiris_backend/files/bankacılık_denetleme_kurumu.pdf"
    #file_path = "aiiris_backend/files/tcmb.pdf"
    #file_path = "aiiris_backend/files/Bilanco.xlsx"
    file_path = "aiiris_backend/files/TUFE.xlsx"
    #file_path = "aiiris_backend/files/VeriSeti.xlsx"
    #file_path = "aiiris_backend/files/İkt.docx"
    #file_path = "aiiris_backend/files/text_file.txt"
    #file_path = "aiiris_backend/files/png_file.png"
    #file_path = "aiiris_backend/files/jpeg_file.jpg"


    if not os.path.exists(file_path):
        print(f"X Hata: {file_path} dosyası bulunamadı!")
        return
    
    print(f"Dosya bulundu: {file_path}")
    # Pipeline'ı başlat
    try:
        pipeline = UploadPipeline( file_path=file_path )

        print("Dosya analiz ediliyor...")
        pipeline.run()

    except Exception as e:
        print(f"X Hata oluştu: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()