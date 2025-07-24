import re
from typing import List
from backend.monitoring.metrics import guard_violations_total


HARMFUL_KEYWORDS = {
    "hakaret": ["aptal", "salak", "gerizekalı", "ahmak"],
    "küfür": ["s*k", "a*k", "amk", "mk", "aq", "küfür"],
    "tehdit": ["öldürmek", "tehdit", "zarar vermek", "intikam", "öldür"],
    "ayrımcılık": ["ırkçı", "cinsiyetçi", "ayrımcı", "faşist"],
    "şiddet": ["silah", "bomba", "zehir", "öldür", "intihar"],
    "uyuşturucu": ["eroin", "esrar", "kokain", "metamfetamin", "uyuşturucu"],
    "yasadışı": ["devleti yık", "anayasayı çiğne", "terör", "suikast"],
    "müstehcenlik": ["cinsellik", "porno"],
}


HALLUCINATION_MARKERS = {
    "aşırı_kesinlik": [
        "kesinlikle",
        "mutlaka",
        "asla",
        "hiç şüphesiz",
        "her zaman",
        "100% eminim",
        "net olarak biliyorum",
        "kategorik olarak",
        "garanti ederim",
        "şüphesiz",
    ],
    "belirsizlik": [
        "sanırım",
        "emin değilim",
        "belki",
        "tahminimce",
        "öyle olduğunu düşünüyorum",
        "tam olarak bilemiyorum",
        "hissetmiyorum",
        "uğra",
        "olabilir",
        "olasılıkla",
        "muhtemelen",
        "gibi görünüyor",
    ],
}

# Güvenlik ihlal desenleri
SECURITY_PATTERNS = {
    "sql_injection": [
        r"(\bSELECT\b.*\bFROM\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\b1=1\b--)",
    ],
    "script_injection": [
        r"<script",
        r"javascript:",
        r"onerror=",
        r"onload=",
        r"onclick=",
    ],
    "path_traversal": [r"\.\.\/", r"\.\.\\", r"\.\.%2f", r"\.\.%5c"],
}

# Uydurma bilgi kalıpları
FABRICATION_PATTERNS = [
    r"(\d{4}|20\d{2}) yılında (?!yapılan).*?(?:göstermiştir|kanıtlanmıştır)",
    r"araştırmalar (?:kesinlikle|açıkça) göstermiştir ki",
    r"uzmanların (tamamı|hepsi|tümü) (hemfikirdir|kabul etmektedir)",
]

# Zararlı öneri kalıpları
HARMFUL_ADVICE_PATTERNS = [
    r"(nas[ıi]l.*?hack(le|la|li|er))",
    r"(parola.*?k[ıi]r(ma|mak))",
    r"(yasad[ıi]ş[ıi].*?erişim|erişim.*?yasad[ıi]ş[ıi])",
    r"(sistem.*?ele geçir)",
    r"(güvenlik.*?atla)",
]


def check_input_violations(text: str) -> List[str]:

    if not text or not isinstance(text, str):
        return []

    violations = []
    lower_text = text.lower()

    for category, words in HARMFUL_KEYWORDS.items():
        matched_words = [
            word
            for word in words
            if re.search(rf"\b{re.escape(word)}\b", lower_text, re.IGNORECASE)
        ]
        ## fr deki r raw string demek. re.escape(word) ise kelimenin regex'e uygun hale getirilmesi için kullanılır.
        # Ayrıca \b ile kelimenin başında ve sonunda boşluk olup olmadığını kontrol ediyoruz. kelimenin tam olarak eşleşmesini sağlıyor.
        if matched_words:
            violations.append(
                f"{category.capitalize()} tespit edildi: {', '.join(matched_words)}"
            )
            guard_violations_total.labels(violation_type=category).inc()

    for sec_type, patterns in SECURITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"Güvenlik ihlali: {sec_type.capitalize()}")
                guard_violations_total.labels(violation_type=sec_type).inc()
                break

    return violations


def check_output_violations(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []

    violations = []
    text_lower = text.lower()

    # Aşırı kesinlik kontrolü
    certainity_markers = sum(
        1
        for marker in HALLUCINATION_MARKERS["aşırı_kesinlik"]
        if re.search(rf"\b{re.escape(marker)}\b", text_lower, re.IGNORECASE)
    )
    if certainity_markers >= 3:
        violations.append("Aşırı kesinlik tespit edildi.")
        guard_violations_total.labels(violation_type="aşırı_kesinlik").inc()

    # Belirsizlik kontrolü
    uncertainty_markers = sum(
        1
        for marker in HALLUCINATION_MARKERS["belirsizlik"]
        if re.search(rf"\b{re.escape(marker)}\b", text_lower, re.IGNORECASE)
    )
    if uncertainty_markers >= 3:
        violations.append("Belirsizlik tespit edildi.")
        guard_violations_total.labels(violation_type="belirsizlik").inc()

    # Uydurma bilgi kontrolü
    for pattern in FABRICATION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            violations.append("Uydurma bilgi tespit edildi.")
            guard_violations_total.labels(violation_type="uydurma_bilgi").inc()
            break

    # Zararlı öneri kontrolü
    for pattern in HARMFUL_ADVICE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            violations.append("Zararlı öneri tespit edildi.")
            guard_violations_total.labels(violation_type="zararlı_tavsiye").inc()
            break

    return violations


def sanitize_output(text: str, violation_types: List[str] = None) -> str:
    if not text or not isinstance(text, str):
        return text

    sanitized_text = text

    # Tüm zararlı kelimeleri düzleştir ve birleştir
    all_harmful_keywords = []
    for category, words in HARMFUL_KEYWORDS.items():
        # Belirli bir ihlal türü belirtilmişse, sadece o türdeki kelimeleri sansürlicez
        if violation_types and category not in violation_types:
            continue
        all_harmful_keywords.extend(words)

    # Tüm zararlı kelimeleri sansürle
    for word in all_harmful_keywords:
        pattern = r"\b" + re.escape(word) + r"\b"
        replacement = "[SANSÜRLENDİ]"
        sanitized_text = re.sub(
            pattern, replacement, sanitized_text, flags=re.IGNORECASE
        )

    return sanitized_text


def analyze_text_safety(text: str) -> dict:
    input_violations = check_input_violations(text)
    output_violations = check_output_violations(text)

    # metin güvenliği puanı hesaplıyoruz
    violation_count = len(input_violations) + len(output_violations)
    safety_score = max(0, 100 - (violation_count * 20))  # Her ihlal için 20 puan düşer

    return {
        "input_violations": input_violations,
        "output_violations": output_violations,
        "safety_score": safety_score,
        "is_safe": safety_score >= 60,  # Güvenli kabul etmek için 60 ve üzeri puan
        "sanitized_text": sanitize_output(text) if violation_count > 0 else text,
    }
