import openai
from typing import Dict
from backend.monitoring.metrics import guard_violations_total


def check_openai_moderation(text: str) -> Dict:
    """
    Check text using OpenAI's moderation API
    Returns a dictionary with moderation results
    """
    if not text or not isinstance(text, str):
        return {
            "flagged": False,
            "categories": {},
            "category_scores": {},
            "violations": [],
        }

    try:
        response = openai.moderations.create(input=text)
        result = response.results[0]

        violations = []

        # Check if any category is flagged
        if result.flagged:
            for category, flagged in result.categories.__dict__.items():
                if flagged:
                    violations.append(f"OpenAI moderation flagged: {category}")
                    guard_violations_total.labels(violation_type=category).inc()

        return {
            "flagged": result.flagged,
            "categories": result.categories.__dict__,
            "category_scores": result.category_scores.__dict__,
            "violations": violations,
        }

    except Exception as e:
        print(f"OpenAI moderation error: {e}")
        return {
            "flagged": False,
            "categories": {},
            "category_scores": {},
            "violations": [f"Moderation error: {str(e)}"],
        }
