import os
import fitz
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat, AnalyzeDocumentRequest, AnalyzeOutputOption
import uuid
import base64
from backend.shared.constants import document_intelligence_client, IMAGES_PATH_STR

def analyze_document(file_path: str):
    pdf = fitz.open(file_path)
    pdf_bytes = pdf.tobytes()

    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout",
        AnalyzeDocumentRequest(bytes_source=pdf_bytes),
        output_content_format=DocumentContentFormat.MARKDOWN,
        output=[AnalyzeOutputOption.FIGURES]
    )

    result: AnalyzeResult = poller.result()
    operation_id = poller.details["operation_id"]

    figure_images = {}
    os.makedirs(IMAGES_PATH_STR, exist_ok=True)

    if result.figures:
        for figure_idx, figure in enumerate(result.figures):
            figure_id = f"fig_{uuid.uuid4().hex[:8]}"
            figure_caption = figure.caption.content if figure.caption else ""

            if figure.id:
                response = document_intelligence_client.get_analyze_result_figure(
                    model_id=result.model_id,
                    result_id=operation_id,
                    figure_id=figure.id
                )

                img_data = b"".join(response)

                img_base64 = base64.b64encode(img_data).decode()

                image_filename = f"{figure_id}.png"
                image_path = os.path.join(IMAGES_PATH_STR, image_filename)

                with open(image_path, "wb") as writer:
                    writer.write(img_data)

                figure_images[figure_id] = {
                    'base64': img_base64,
                    'caption': figure_caption,
                    'image_path': image_path,
                }
    else:
        print("No figures found.")

    markdown_content = result.content

    for figure_id, figure_data in figure_images.items():
        figure_tag_start = markdown_content.find('<figure>')
        if figure_tag_start != -1:
            figure_tag_end = markdown_content.find('</figure>', figure_tag_start) + 9

            figure_markdown = f"\n\n[{figure_caption} ** ID:`{figure_id}]`**"

            markdown_content = markdown_content[:figure_tag_start] + figure_markdown + markdown_content[
                figure_tag_end:]

    output_path = "C:/Users/ASUS/Desktop/Coding/CanProjects/AIris/backend/database/uploads/tcmb.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    pdf.close()

if __name__ == "__main__":
    sample_path = "C:/Users/ASUS/Desktop/Coding/CanProjects/AIris/backend/database/uploads/tcmb.pdf"
    analyze_document(sample_path)