import uuid
import json
from typing import List
from backend.shared.constants import async_text_analytics_client, MASKED_MAP_JSON_PATH
from backend.shared.logger import get_logger

logger = get_logger("PII")

categories_to_filter=["Person", "PhoneNumber", "Address", "IPAddress", "Email", "USUKPassportNumber",
          "USBankAccountNumber",
          "USDriversLicenseNumber",
          "USIndividualTaxpayerIdentification",
          "USSocialSecurityNumber","TRNationalIdentificationNumber"]

async def mask_text(docs: List[str], id: str) -> List[str]:
    """Mask PII entities in the given text using Azure Text Analytics."""
    result = await async_text_analytics_client.recognize_pii_entities(
        documents=docs,
        string_index_type="UnicodeCodePoint",
        disable_service_logs=True,
        model_version="latest",
        categories_filter=categories_to_filter,
    )

    masked_texts = []
    masked_map = {}

    for i, doc_result in enumerate(result):
        if not doc_result.is_error:
            masked_text = getattr(doc_result, "redacted_text", "NR - " + docs[i])
            sorted_entities = sorted(doc_result.entities, key=lambda e: e.offset)
            masked_spans = []
            for entity in sorted_entities:
                cat = entity.category.lower()
                unique_id = str(uuid.uuid4())[:8]
                mask = f"[{cat}-{unique_id}]"
                masked_spans.append((entity.offset, entity.length, mask, entity.text))
                masked_map[mask] = entity.text
            for offset, length, mask, _ in reversed(masked_spans):
                masked_text = masked_text[:offset] + mask + masked_text[offset + length:]
            masked_texts.append(masked_text)
        else:
            masked_texts.append(docs[i])
            logger.error(f"Error processing document {i}: {doc_result.error}")

    try:
        with open(MASKED_MAP_JSON_PATH, "r", encoding="utf-8") as f:
            existing_map = json.load(f)
    except:
        logger.info("No existing map found, creating a new one.")
        existing_map = {}

    existing_map[id] = masked_map

    with open(MASKED_MAP_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_map, f, ensure_ascii=False, indent=4)

    return masked_texts


def unmask_text(text):
    """Unmask PII entities in the given text using a predefined mapping."""
    try:
        with open(MASKED_MAP_JSON_PATH, "r", encoding="utf-8") as f:
            masked_map = json.load(f)
    except:
        logger.warning("No existing map found, returning text as is.")
        return text

    for id_map in masked_map.values():
        for mask, original in id_map.items():
            text = text.replace(mask, original) # Replace all mask tokens in text with their originals from all ids
    return text