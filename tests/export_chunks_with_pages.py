#!/usr/bin/env python3
"""
Export parsed chunks with assigned page numbers to JSON.

Usage:
  python tests/export_chunks_with_pages.py "<input_pdf_path>" "<output_json_path>"
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.pipeline.vector import PreEmbeddingProcess, VectorStorePipeline
from backend.utils.parser import AzureParser


PAGE_MARKER_RE = re.compile(r"<!-- PAGE_BREAK:(\d+) -->")


def assign_page_numbers_and_clean_chunks(docs, document_name: str):
    """Assign starting page number per chunk and remove page markers."""
    current_page = 1
    exported_chunks = []

    for idx, doc in enumerate(docs):
        first_marker = PAGE_MARKER_RE.search(doc.page_content)
        if first_marker is None:
            page_number = current_page
        else:
            pre_marker = doc.page_content[: first_marker.start()].strip()
            page_number = current_page if pre_marker else int(first_marker.group(1))
            all_markers = PAGE_MARKER_RE.findall(doc.page_content)
            current_page = int(all_markers[-1])

        cleaned_content = PAGE_MARKER_RE.sub("", doc.page_content).strip()
        exported_chunks.append(
            {
                "chunk_id": f"chunk_{idx}",
                "file_name": document_name,
                "page_number": page_number,
                "page_content": cleaned_content,
            }
        )

    return exported_chunks


async def export_chunks(input_path: Path, output_path: Path):
    document_name = input_path.stem

    parsed = await AzureParser(str(input_path), photo_less_mode=True)
    if isinstance(parsed, tuple):
        text_content, _figure_images = parsed
    else:
        text_content = parsed

    pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.NONE)
    docs = pipeline.text_splitter.create_documents([text_content])
    chunks = assign_page_numbers_and_clean_chunks(docs, document_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "document_name": document_name,
                "input_file": str(input_path),
                "chunk_count": len(chunks),
                "chunks": chunks,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Exported {len(chunks)} chunks")
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Export document chunks with assigned page numbers to JSON."
    )
    parser.add_argument("input_file", help="Absolute path to input PDF/DOCX file")
    parser.add_argument("output_file", help="Absolute path to output JSON file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = Path(args.output_file)
    asyncio.run(export_chunks(input_path, output_path))


if __name__ == "__main__":
    main()