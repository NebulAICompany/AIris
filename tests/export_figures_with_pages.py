#!/usr/bin/env python3
"""
Export extracted figures and assigned page numbers to JSON.

Usage:
  python tests/export_figures_with_pages.py "<input_pdf_path>" "<output_json_path>"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.utils.parser import AzureParser


async def export_figures(input_path: Path, output_path: Path):
    parsed = await AzureParser(str(input_path), photo_less_mode=False)
    if isinstance(parsed, tuple):
        _content, figure_images = parsed
    else:
        figure_images = {}

    figures = []
    for figure_id, data in figure_images.items():
        figures.append(
            {
                "figure_id": figure_id,
                "caption": data.get("caption", ""),
                "page_number": data.get("page_number"),
                "image_path": data.get("image_path", ""),
            }
        )

    output = {
        "document_name": input_path.stem,
        "input_file": str(input_path),
        "figure_count": len(figures),
        "figures": figures,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(figures)} figure(s)")
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Export figure metadata and page numbers to JSON."
    )
    parser.add_argument("input_file", help="Absolute path to input PDF/DOCX file")
    parser.add_argument("output_file", help="Absolute path to output JSON file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    asyncio.run(export_figures(input_path, Path(args.output_file)))


if __name__ == "__main__":
    main()
