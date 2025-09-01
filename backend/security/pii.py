import uuid
import json
from typing import List
from rapidfuzz import fuzz, process
from backend.shared.constants import async_text_analytics_client, MASKED_MAP_JSON_PATH
from backend.shared.logger import get_logger

logger = get_logger("PII")

categories_to_filter = [
    "Person",
    "PhoneNumber",
    "Address",
    "IPAddress",
    "Email",
    "USUKPassportNumber",
    "USBankAccountNumber",
    "USDriversLicenseNumber",
    "USIndividualTaxpayerIdentification",
    "USSocialSecurityNumber",
    "TRNationalIdentificationNumber",
]

SIMILARITY_THRESHOLD = 75.0


def get_or_create_uuid(
    entity_text: str, entity_category: str, existing_map: dict
) -> str:
    """Get existing UUID for similar entity with same category or create new one."""
    # Flatten all existing entities with their categories from all IDs
    all_existing_entities_with_categories = []
    for id_map in existing_map.values():
        for mask, original in id_map.items():
            # Extract category from mask (format: [category-uuid])
            category = mask.split("-")[0][1:]  # Remove the opening bracket
            all_existing_entities_with_categories.append((original, category))

    if not all_existing_entities_with_categories:
        return str(uuid.uuid4())[:8]

    # Find the best match among existing entities with SAME category
    best_match = None
    best_score = 0

    for existing_text, existing_category in all_existing_entities_with_categories:
        # Only compare if categories match
        if existing_category.lower() == entity_category.lower():
            score = fuzz.ratio(entity_text, existing_text)
            if score > best_score:
                best_score = score
                best_match = (existing_text, existing_category)

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        # Find the mask (UUID) for the similar entity with same category
        for id_map in existing_map.values():
            for mask, original in id_map.items():
                if original == best_match[0]:
                    # Extract UUID from mask (format: [category-uuid])
                    return mask.split("-")[1][:-1]  # Remove the closing bracket

    # Generate new UUID if no similar entity with same category found
    return str(uuid.uuid4())[:8]


async def mask_text(docs: List[str], id: str) -> List[str]:
    """Mask PII entities in the given text using Azure Text Analytics."""
    # Load existing mappings first
    try:
        with open(MASKED_MAP_JSON_PATH, "r", encoding="utf-8") as f:
            existing_map = json.load(f)
    except:
        logger.info("No existing map found, creating a new one.")
        existing_map = {}

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
                unique_id = get_or_create_uuid(entity.text, cat, existing_map)
                mask = f"[{cat}-{unique_id}]"
                masked_spans.append((entity.offset, entity.length, mask, entity.text))
                masked_map[mask] = entity.text
            for offset, length, mask, _ in reversed(masked_spans):
                masked_text = (
                    masked_text[:offset] + mask + masked_text[offset + length :]
                )
            masked_texts.append(masked_text)
        else:
            masked_texts.append(docs[i])
            logger.error(f"Error processing document {i}: {doc_result.error}")

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
            text = text.replace(
                mask, original
            )  # Replace all mask tokens in text with their originals from all ids
    return text
