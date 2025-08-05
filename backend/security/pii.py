import uuid
import json
from pathlib import Path
from backend.shared.constants import text_analytics_client, MASKED_MAP_JSON_PATH
from backend.shared.logger import get_logger

logger = get_logger("PII")


def mask_text(text):
    """Mask PII entities in the given text using Azure Text Analytics."""
    result = text_analytics_client.recognize_pii_entities(
        documents=[text],
        string_index_type="UnicodeCodePoint",
        disable_service_logs=True,
        model_version="latest",
    )

    masked_map = {}
    if not result[0].is_error:
        masked_text = getattr(result[0], "redacted_text", "NR - " + text)
        sorted_entities = sorted(result[0].entities, key=lambda e: e.offset)
        masked_spans = []
        for entity in sorted_entities:
            cat = entity.category.lower()
            unique_id = str(uuid.uuid4())[:8]
            mask = f"[{cat}-{unique_id}]"
            masked_spans.append((entity.offset, entity.length, mask, entity.text))
            masked_map[mask] = entity.text
        for offset, length, mask, _ in reversed(masked_spans):
            masked_text = masked_text[:offset] + mask + masked_text[offset + length:]
    else:
        masked_text = text
        logger.error(f"Error: {result[0].error}")

    try:
        with open(MASKED_MAP_JSON_PATH, "r", encoding="utf-8") as f:
            existing_map = json.load(f)
    except:
        logger.info("No existing map found, creating a new one.")
        existing_map = {}

    existing_map.update(masked_map)

    with open(MASKED_MAP_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_map, f, ensure_ascii=False, indent=4)

    return masked_text


def unmask_text(text):
    """Unmask PII entities in the given text using a predefined mapping."""
    try:
        with open(MASKED_MAP_JSON_PATH, "r", encoding="utf-8") as f:
            masked_map = json.load(f)
    except:
        logger.warning("No existing map found, returning text as is.")
        return text

    for mask, original in masked_map.items():
        text = text.replace(mask, original)
    return text