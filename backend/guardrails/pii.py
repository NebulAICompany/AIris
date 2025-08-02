import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from dotenv import load_dotenv
import uuid
import json
from pathlib import Path

load_dotenv()

endpoint = os.environ["AZURE_LANGUAGE_ENDPOINT"]
key = os.environ["AZURE_LANGUAGE_KEY"]
map_base_location = Path(__file__).parent.parent / "database" / "masked_map.json"

text_analytics_client = TextAnalyticsClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

def mask_text(text):
    """Mask PII entities in the given text using Azure Text Analytics."""
    result = text_analytics_client.recognize_pii_entities(
        documents=[text],
        string_index_type="UnicodeCodePoint",
        disable_service_logs=True,
        model_version="latest",
    )

    masked_map = {}
    for idx, doc in enumerate(result):
        if not doc.is_error:
            masked_text = text[idx]
            sorted_entities = sorted(doc.entities, key=lambda e: e.offset)
            masked_spans = []
            for entity in sorted_entities:
                cat = entity.category.lower()
                unique_id = str(uuid.uuid4())[:8]
                mask = f"[{cat}-{unique_id}]"
                masked_spans.append((entity.offset, entity.length, mask, entity.text))
                masked_map[mask] = entity.text
            for offset, length, mask, _ in reversed(masked_spans):
                masked_text = masked_text[:offset] + mask + masked_text[offset+length:]
        else:
            print(f"Error: {doc.error}")

    try:
        with open(map_base_location, "r", encoding="utf-8") as f:
            existing_map = json.load(f)
    except:
        print("No existing map found, creating a new one.")
        existing_map = {}

    existing_map.update(masked_map)

    with open(map_base_location, "w", encoding="utf-8") as f:
        json.dump(existing_map, f, ensure_ascii=False, indent=4)

    return masked_text, masked_map


def unmask_text(text):
    """Unmask PII entities in the given text using a predefined mapping."""
    with open(map_base_location, "r", encoding="utf-8") as f:
        masked_map = json.load(f)
    for mask, original in masked_map.items():
        text = text.replace(mask, original)
    return text
