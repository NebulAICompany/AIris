import re
from typing import Tuple, Dict
import json
import hashlib

# Comprehensive PII patterns combining both modules
PII_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b",
    "TC": r"\b[1-9][0-9]{10}\b",  # 11-haneli TC Kimlik No, ilk rakam 0 olamaz
    "IBAN": r"\bTR\d{2}(?:\s?\d{4}){4,5}\b",  # TR ile başlayan, 26 haneli IBAN, boşluk opsiyonel
    "PHONE": r"\b(?:\+90|0)?\s?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b",  # Türkçe telefon formatları
    "VERGI_NO": r"\b\d{10}\b",  # 10-haneli vergi numarası
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",  # Kredi kartı numarası (13-16 hane, boşluk/tire olabilir)
    "PASSPORT": r"\b[A-Z][0-9]{7,8}\b",  # Türk pasaport numarası (örnek: U1234567)
    "ADDRESS": r"\b(?:Mah\.|Sok\.|Cad\.|Blok|Apt\.|No:?\s?\d+)\b",  # Basit adres anahtar kelimeleri
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",  # US Social Security Number
    # Daha fazla PII türü eklenebilir...
}


def pii_mask(text: str, mapping_json_path: str = None) -> Tuple[str, Dict[str, str]]:
    """
    Masks PII in the text with unique tokens (using hash of PII and type) and returns the masked text and a mapping.
    This is the enhanced version from pii_deneme.py with comprehensive patterns.
    """
    if not text:
        return text, {}

    mapping = {}

    def make_mask_func(pii_type):
        def mask_match(match):
            pii_value = match.group(0)
            hash_digest = hashlib.sha256(pii_value.encode("utf-8")).hexdigest()[:10]
            key = f"<{pii_type}_{hash_digest}>"
            mapping[key] = pii_value
            return key

        return mask_match

    masked_text = text
    for pii_type, pattern in PII_PATTERNS.items():
        masked_text = re.sub(pattern, make_mask_func(pii_type), masked_text)

    if mapping_json_path:
        save_mapping_to_json(mapping, mapping_json_path)

    return masked_text, mapping


def mask_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Alternative PII masking function with simpler placeholder format.
    This is the version from pii_masker.py for backward compatibility.
    """
    if not text:
        return text, {}

    mask_map = {}
    masked_text = text
    counters = {}

    for pii_type, pattern in PII_PATTERNS.items():
        matches = list(re.finditer(pattern, masked_text))

        for match in matches:
            original = match.group()
            count = counters.get(pii_type, 0) + 1
            placeholder = f"[[{pii_type}_{count}]]"

            masked_text = masked_text.replace(original, placeholder, 1)
            mask_map[placeholder] = original
            counters[pii_type] = count + 1

    return masked_text, mask_map


def save_mapping_to_json(mapping: Dict[str, str], filepath: str):
    """Save PII mapping to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def load_mapping_from_json(filepath: str) -> Dict[str, str]:
    """Load PII mapping from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def pii_unmask(
    masked_text: str, mapping: Dict[str, str] = None, mapping_json_path: str = None
) -> str:
    """
    Replaces mask tokens in the text with the original PII using the mapping.
    If mapping is not provided, loads it from mapping_json_path.
    This works with both hash-based and simple placeholder formats.
    """
    if not masked_text:
        return masked_text

    if mapping is None and mapping_json_path:
        mapping = load_mapping_from_json(mapping_json_path)

    if not mapping:
        return masked_text

    unmasked_text = masked_text
    for key, value in mapping.items():
        unmasked_text = unmasked_text.replace(key, value)
    return unmasked_text


def unmask_pii(text: str, mask_map: Dict[str, str]) -> str:
    """
    Alternative unmasking function for backward compatibility.
    This is the version from pii_masker.py.
    """
    if not text:
        return text

    result = text
    for placeholder, original in mask_map.items():
        result = result.replace(placeholder, original)

    return result


# Example usage:
if __name__ == "__main__":
    sample = "Contact John at 123-45-6789 or john.doe@example.com or 5551234567."
    mapping_path = "pii_mapping.json"

    # Test enhanced pii_mask function
    masked, mapping = pii_mask(sample, mapping_json_path=mapping_path)
    print("Enhanced Masked:", masked)
    print("Enhanced Mapping:", mapping)

    # Test simple mask_pii function
    masked_simple, mask_map = mask_pii(sample)
    print("Simple Masked:", masked_simple)
    print("Simple Mask Map:", mask_map)

    # Test unmasking
    loaded_mapping = load_mapping_from_json(mapping_path)
    unmasked = pii_unmask(masked, mapping=loaded_mapping)
    print("Unmasked:", unmasked)
