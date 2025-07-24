import re
from typing import Tuple, Dict

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


def mask_pii(text: str) -> Tuple[str, Dict[str, str]]:
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


def unmask_pii(text: str, mask_map: Dict[str, str]) -> str:
    if not text:
        return text

    result = text
    for placeholder, original in mask_map.items():
        result = result.replace(placeholder, original)

    return result
