import re
import logging
from typing import Tuple, Literal
from backend.libs.logger import get_logger

# Dil tespiti için
try:
    from langdetect import detect as langdetect_detect

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    import jpype
    import os
    from jpype import JClass, getDefaultJVMPath, startJVM

    # Start JVM for zemberek
    if not jpype.isJVMStarted():
        jvmPath = getDefaultJVMPath()
        print(f"JVM Path: {jvmPath}")
        zemberek_path = os.path.join(
            os.path.dirname(__file__), "..", "libs", "zemberek-full.jar"
        )
        startJVM(jvmPath, "-ea", f"-Djava.class.path={zemberek_path}")

    # Initialize Zemberek classes
    TurkishMorphology = JClass("zemberek.morphology.TurkishMorphology")
    turkish_morphology = TurkishMorphology.createWithDefaults()

    TurkishSpellChecker = JClass("zemberek.normalization.TurkishSpellChecker")
    turkish_spell_checker = TurkishSpellChecker(turkish_morphology)

    ZEMBEREK_AVAILABLE = True

except ImportError as e:
    turkish_spell_checker = None
    ZEMBEREK_AVAILABLE = False
    logging.error(f"Zemberek library not found: {e}")


logger = get_logger("QUERY_UTILS")

# Niyet tipleri
IntentType = Literal[
    "özet", "trend", "analiz", "karşılaştırma", "tahmin", "soru", "bilinmeyen"
]


def clean_query(query: str) -> str:
    if not query or not isinstance(query, str):
        return ""

    # URL'leri temizle
    query = re.sub(
        r"https?://\S+|www\.\S+|\.com|\.org|\.net|\.edu|\.gov|\.io|\.co|\.ai", "", query
    )

    # Özel karakterleri ve emojileri temizle (Türkçe karakterleri koru)
    query = re.sub(r'[^\w\sçğıöşüÇĞİÖŞÜ,.?!;:()\[\]{}\'"-]', "", query)

    # Fazla boşlukları temizle
    query = re.sub(r"\s+", " ", query)

    # Baş ve sondaki boşlukları temizle
    query = query.strip()

    return query


def spell_check(query: str) -> str:
    if not query or not isinstance(query, str):
        return ""

    if not ZEMBEREK_AVAILABLE:
        logger.warning("Zemberek is not available. Skipping spell check.")
        return query

    try:
        words = query.split()
        corrected = []

        for word in words:
            # Sadece noktalama işaretlerinden oluşan kelimeleri atla
            if all(c in ",.?!;:()[]{}'\"-" for c in word):
                corrected.append(word)
                continue

            normalized_word = normalize_repeated_chars(word)

            # Yazım hatası kontrolü ve düzeltme önerisi
            if not turkish_spell_checker.check(normalized_word):
                suggestions = turkish_spell_checker.suggestForWord(normalized_word)
                if suggestions and len(suggestions) > 0:
                    corrected.append(str(suggestions[0]))
                else:
                    corrected.append(normalized_word)
            else:
                corrected.append(normalized_word)
        return " ".join(corrected)

    except Exception as e:
        logger.error(f"Error in spell checking: {e}")
        return query


def detect_language(query: str) -> str:
    if not query or not isinstance(query, str) or len(query.strip()) < 3:
        return "unknown"
    if not LANGDETECT_AVAILABLE:
        logger.warning("Langdetect is not available. Skipping language detection.")
        return "unknown"

    try:
        return langdetect_detect(query)
    except Exception as e:
        logger.error(f"Error in language detection: {e}")
        return "unknown"


def detect_intent(query: str) -> Tuple[IntentType, float]:
    if not query or not isinstance(query, str):
        return ("bilinmeyen", 0.0)

    query = query.lower()

    intent_keywords = {
        "özet": [
            "özet",
            "özetle",
            "özetler",
            "özetlemek",
            "özeti",
            "özetini",
            "özetleyebilir",
            "kısaca",
            "özetçe",
        ],
        "trend": [
            "trend",
            "eğilim",
            "yönelim",
            "artış",
            "azalış",
            "grafik",
            "gidişat",
            "zaman serisi",
            "değişim",
        ],
        "analiz": [
            "analiz",
            "analizi",
            "değerlendirme",
            "inceleme",
            "çözümleme",
            "neden",
            "ilişki",
            "detay",
            "detaylı",
        ],
        "karşılaştırma": [
            "karşılaştır",
            "kıyasla",
            "karşılaştırma",
            "fark",
            "benzerlik",
            "arasındaki",
            "kıyas",
        ],
        "tahmin": [
            "tahmin",
            "öngörü",
            "beklenti",
            "gelecek",
            "olacak",
            "olur mu",
            "olabilir",
        ],
        "soru": [
            "kim",
            "ne",
            "nedir",
            "kaç",
            "neden",
            "nasıl",
            "nerede",
            "ne zaman",
            "hangi",
        ],
    }

    max_score = 0.0
    detected_intent: IntentType = "bilinmeyen"

    for intent, keywords in intent_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in query:
                score += 1

            normalized_score = score / len(keywords) if keywords else 0
            if normalized_score > max_score:
                max_score = normalized_score
                detected_intent = intent

    if max_score < 0.1:
        return ("bilinmeyen", max_score)

    return (detected_intent, max_score)


def normalize_repeated_chars(word: str) -> str:
    if not word or not isinstance(word, str):
        return word

    result = []
    i = 0

    while i < len(word):
        char = word[i]
        result.append(char)
        repeat_count = 1

        j = i + 1
        while j < len(word) and word[j] == char:
            repeat_count += 1
            j += 1

            if repeat_count == 2:
                result.append(char)

        i = j

    return "".join(result)
