# Save uploaded file
file_path = "C:/Users/ASUS/Desktop/Coding/Python/vectorrag/Esra/pdf_file.pdf"
# Process the uploaded file
from aiiris_backend.orchestrator.upload_orchestrator import process_file
result = process_file(str(file_path))
print(result)
