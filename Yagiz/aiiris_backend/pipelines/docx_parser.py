import base64
import subprocess
import openai
from docx import Document
from pathlib import Path
from docx.oxml.ns import qn
from pipelines.uploadpipe import UploadPipeline
import subprocess
from docx2pdf import convert


class DocxParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.device = "cpu"
    
    

    def run(self):
        doc = Document(self.pdf_path)

        save_dir = Path(__file__).resolve().parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        pdf_stem = Path(self.pdf_path).stem
        txt_output_path = save_dir / f"{pdf_stem}_txt.txt"

        image_count = 0
        page_num = 1

        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(f"\n--- Page {page_num} ---\n")

            for block in doc._body._element.iterchildren():
                tag = block.tag

                # Paragraph
                if tag == qn("w:p"):
                    para = block
                    texts = []
                    for node in para.iter():
                        # detect text runs
                        if node.tag == qn("w:t") and node.text:
                            texts.append(node.text)
                        # detect page breaks
                        elif node.tag == qn("w:br") and node.get(qn("w:type")) == "page":
                            page_num += 1
                            f.write(f"\n--- Page {page_num} ---\n")

                    f.write(" ".join(texts) + "\n")

                    # Check for inline images in this paragraph
                    for blip in para.xpath(".//a:blip"):
                        rel_id = blip.attrib[qn("r:embed")]
                        image_part = doc.part.related_parts[rel_id]
                        image_bytes = image_part.blob

                        image_count += 1
                        description = self.describe_image(image_bytes)
                        f.write(f"\n[Image {image_count}]")
                        f.write(f"\n[Image Description]: {description}\n")
                        f.write("---\n")

                # Table
                elif tag == qn("w:tbl"):
                    table = block
                    for row in table.xpath(".//w:tr"):
                        for cell in row.xpath(".//w:tc"):
                            texts = [t.text for t in cell.xpath(".//w:t") if t.text]
                            f.write(" | ".join(texts) + "\n")
                
                f.write("\n")


    

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
    def convert_docx_to_pdf(self,input_path, output_dir):
        convert(input_path, output_dir)
        #     subprocess.run([
        #         "soffice",
        #         "--headless",
        #         "--convert-to", "pdf",
        #         input_path,
        #         "--outdir", output_dir
        # ], check=True)        

if __name__ == "__main__":
    parser = DocxParser("uploads/İkt.docx")
    parser.convert_docx_to_pdf("uploads/İkt.docx", "uploads")
    
    pdf_stem = Path("uploads/İkt.pdf").stem
    pdf_path = str(Path("uploads") / f"{pdf_stem}.pdf")
    
    if not Path(pdf_path).exists():
        print(f"PDF dosyası bulunamadı: {pdf_path}")
    else:
        pipe = UploadPipeline(pdf_path)
        pipe.run()
        print("DOCX to PDF ve UploadPipeline işlemi tamamlandı.")