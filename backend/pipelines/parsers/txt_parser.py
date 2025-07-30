class TxtParser:
    def __init__(self, file_path: str, txt_output_path: str):
        self.file_path = file_path
        self.txt_output_path = txt_output_path
    
    def run(self):

        with open(self.file_path, "r", encoding="utf-8") as infile, open(
            self.txt_output_path, "w", encoding="utf-8"
        ) as outfile:
            for line in infile:
                if line.strip():  # satır boş değilse
                    outfile.write(line)

        return self.txt_output_path
