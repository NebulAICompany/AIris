import os
import requests
import xml.etree.ElementTree as ET
from agents import function_tool


def wolfram_alpha_query_custom(query: str, app_id: str) -> str:
    """
    Custom Wolfram Alpha query function that bypasses the Content-Type issue
    """
    url = "http://api.wolframalpha.com/v2/query"
    params = {"input": query, "appid": app_id, "output": "XML"}

    try:
        response = requests.get(url, params=params)

        if response.status_code != 200:
            return f"Error: HTTP {response.status_code}"

        # Parse XML response
        root = ET.fromstring(response.text)

        # Check if query was successful
        if root.get("success") != "true":
            return "Error: Query was not successful"

        # Find pods with results
        pods = root.findall("pod")

        for pod in pods:
            title = pod.get("title", "Unknown")

            # Look for subpods with plaintext
            subpods = pod.findall("subpod")
            for subpod in subpods:
                plaintext = subpod.find("plaintext")
                if plaintext is not None and plaintext.text:
                    # Return the first meaningful result
                    if title in ["Result", "Decimal approximation", "Solutions"]:
                        return plaintext.text

        # If no specific result pod found, return first available text
        for pod in pods:
            subpods = pod.findall("subpod")
            for subpod in subpods:
                plaintext = subpod.find("plaintext")
                if plaintext is not None and plaintext.text:
                    return plaintext.text

        return "No results found"

    except Exception as e:
        return f"Error: {str(e)}"


@function_tool
def wolfram_alpha_query(query: str) -> str:
    """
    Perform mathematical calculations, scientific computations, and get factual data using Wolfram Alpha.

    Args:
        query: The query to send to Wolfram Alpha (e.g., 'solve x^2 + 2x + 1 = 0', 'population of Tokyo', 'derivative of sin(x)')

    Returns:
        The result from Wolfram Alpha as a string
    """
    try:
        app_id = os.getenv("WOLFRAM_APP_ID")
        if not app_id:
            return "Error: WOLFRAM_APP_ID environment variable not set"

        return wolfram_alpha_query_custom(query, app_id)

    except Exception as e:
        return f"Error querying Wolfram Alpha: {str(e)}"
