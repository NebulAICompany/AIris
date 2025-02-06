from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# Load the PDF file
pdf_path = "C:/Users/ASUS/Desktop/Coding/Python/vectorrag/20250114-pages-14.pdf"  # Change this to your PDF file path
doc = DocumentFile.from_pdf(pdf_path)

# Load the OCR model (pretrained)
model = ocr_predictor(pretrained=True, reco_arch="parseq")

# Perform OCR
result = model(doc)

# Convert result to structured text
extracted_text = result.export()

# Print extracted text
for page_num, page in enumerate(extracted_text["pages"], start=1):
    print(f"\n--- Page {page_num} ---")
    for block in page["blocks"]:
        for line in block["lines"]:
            print(" ".join(word["value"] for word in line["words"]))

# Save extracted text to a file (optional)
with open("extracted_text.txt", "w", encoding="utf-8") as f:
    for page_num, page in enumerate(extracted_text["pages"], start=1):
        f.write(f"\n--- Page {page_num} ---\n")
        for block in page["blocks"]:
            for line in block["lines"]:
                f.write(" ".join(word["value"] for word in line["words"]) + "\n")

print("\n✅ Text extraction complete! Saved to 'extracted_text.txt'")
