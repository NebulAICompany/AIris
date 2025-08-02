import logging
import os
from dotenv import load_dotenv
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

language_key = os.environ.get('AZURE_LANGUAGE_KEY')
language_endpoint = os.environ.get('AZURE_LANGUAGE_ENDPOINT')

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
    try:
        ta_credential = AzureKeyCredential(language_key)
        text_analytics_client = TextAnalyticsClient(
            endpoint=language_endpoint,
            credential=ta_credential)

        response = text_analytics_client.detect_language(documents=[query], country_hint='tr')[0]
        return response.primary_language.name

    except Exception as err:
        print("Encountered exception. {}".format(err))


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


if __name__ == "__main__":
    # Test the functions
    test_query = "Bu bir test cümlesidir. Bu cümledeki yazım hatalarını kontrol et."
    print("Original Query:", test_query)
    print("Detected Language:", detect_language(test_query))
