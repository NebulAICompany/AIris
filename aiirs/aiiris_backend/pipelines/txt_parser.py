import os
from pathlib import Path


class TxtParser:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def run(self):
        # Dosya adı ve uploads klasörünü ayarla
        save_dir = Path(__file__).resolve().parent.parent / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        txt_stem = Path(self.file_path).stem
        output_path = save_dir / f"{txt_stem}_txt.txt"

        with open(self.file_path, "r", encoding="utf-8") as infile, open(
            output_path, "w", encoding="utf-8"
        ) as outfile:
            for line in infile:
                if line.strip():  # satır boş değilse
                    outfile.write(line)

        print(f"Boş olmayan satırlar {output_path} dosyasına yazıldı.")
        return output_path
