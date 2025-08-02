import logging

try:
    import jpype
    import os
    from jpype import JClass, getDefaultJVMPath, startJVM

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



def spell_check(query: str) -> str:
    if not query or not isinstance(query, str):
        return ""

    if not ZEMBEREK_AVAILABLE:
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
        return query


def detect_language(query: str) -> str:
    # if not query or not isinstance(query, str) or len(query.strip()) < 3:
    #     return "unknown"
    # if not LANGDETECT_AVAILABLE:
    #     logger.warning("Langdetect is not available. Skipping language detection.")
    #     return "unknown"
    #
    # try:
    #     return langdetect_detect(query)
    # except Exception as e:
    #     logger.error(f"Error in language detection: {e}")
    return "unknown"


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
