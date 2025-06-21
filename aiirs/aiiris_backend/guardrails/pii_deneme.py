import re
from typing import Tuple, Dict
import json
import hashlib

PII_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b",
    "TC": r"\b[1-9][0-9]{10}\b",  # 11-haneli TC Kimlik No, ilk rakam 0 olamaz
    "IBAN": r"\bTR\d{2}(?:\s?\d{4}){4,5}\b",  # TR ile başlayan, 26 haneli IBAN, boşluk opsiyonel
    "PHONE": r"\b(?:\+90|0)?\s?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b",  # Türkçe telefon formatları
    "VERGI_NO": r"\b\d{10}\b",  # 10-haneli vergi numarası
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",  # Kredi kartı numarası (13-16 hane, boşluk/tire olabilir)
    "PASSPORT": r"\b[A-Z][0-9]{7,8}\b",  # Türk pasaport numarası (örnek: U1234567)
    "ADDRESS": r"\b(?:Mah\.|Sok\.|Cad\.|Blok|Apt\.|No:?\s?\d+)\b",  # Basit adres anahtar kelimeleri
    # Daha fazla PII türü eklenebilir...
}


def pii_mask(text: str, mapping_json_path: str = None) -> Tuple[str, Dict[str, str]]:
    """
    Masks PII in the text with unique tokens (using hash of PII and type) and returns the masked text and a mapping.
    """
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
    for pattern, pii_type in PII_PATTERNS:
        masked_text = re.sub(pattern, make_mask_func(pii_type), masked_text)

    if mapping_json_path:
        save_mapping_to_json(mapping, mapping_json_path)

    return masked_text, mapping


def save_mapping_to_json(mapping: Dict[str, str], filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def load_mapping_from_json(filepath: str) -> Dict[str, str]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def pii_unmask(
    masked_text: str, mapping: Dict[str, str] = None, mapping_json_path: str = None
) -> str:
    """
    Replaces mask tokens in the text with the original PII using the mapping.
    If mapping is not provided, loads it from mapping_json_path.
    """
    if mapping is None and mapping_json_path:
        mapping = load_mapping_from_json(mapping_json_path)

    unmasked_text = masked_text
    for key, value in mapping.items():
        unmasked_text = unmasked_text.replace(key, value)
    return unmasked_text


# Example usage:
if __name__ == "__main__":
    sample = "Contact John at 123-45-6789 or john.doe@example.com or 5551234567."
    mapping_path = "pii_mapping.json"
    masked, mapping = pii_mask(sample, mapping_json_path=mapping_path)
    print("Masked:", masked)
    print("Mapping:", mapping)
    # Load mapping from JSON for demonstration
    loaded_mapping = load_mapping_from_json(mapping_path)
    unmasked = pii_unmask(masked, mapping=loaded_mapping)
    print("Unmasked:", unmasked)
