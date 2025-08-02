class TxtParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def run(self):
        content_parts = []
        with open(self.file_path, "r", encoding="utf-8") as infile:
            for line in infile:
                if line.strip():  # satır boş değilse
                    content_parts.append(line)

        extracted_text = "".join(content_parts)
        print(f"TXT text extraction completed. Total length: {len(extracted_text)} characters")
        return extracted_text
