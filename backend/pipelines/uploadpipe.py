from pathlib import Path
import os, logging, warnings, traceback, openai
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


class UploadPipeline:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.device = "cpu"
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def run(self):

        from backend.pipelines.parsers.docx_parser import DocxParser
        from backend.pipelines.parsers.excel_parser import ExcelParser
        from backend.pipelines.parsers.pdf_parser import PdfParser
        from backend.pipelines.parsers.txt_parser import TxtParser
        from backend.pipelines.parsers.image_parser import ImageParser
        
        file_extension = Path(self.file_path).suffix.lower()
        
        save_dir = Path(__file__).resolve().parent.parent / "database"
        save_dir.mkdir(parents=True, exist_ok=True)
        file_stem = Path(self.file_path).stem
        txt_output_path = save_dir / f"{file_stem}_txt.txt"

        if file_extension == '.pdf':
            parser = PdfParser(self.file_path, txt_output_path, self.client)
        elif file_extension == '.docx':
            parser = DocxParser(self.file_path, txt_output_path, self.client)
        elif file_extension in ('.xlsx', '.xls'):
            parser = ExcelParser(self.file_path, txt_output_path, self.client)
        elif file_extension == '.txt':
            parser = TxtParser(self.file_path, txt_output_path)
        elif file_extension in ('.jpg', '.jpeg', '.gif', '.bmp', '.png'):
            parser = ImageParser(self.file_path, txt_output_path, self.client)
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