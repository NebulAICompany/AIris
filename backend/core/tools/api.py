import requests
import xml.etree.ElementTree as ET
from agents import function_tool
from backend.shared.constants import tavily_client, WOLFRAM_APP_ID

@function_tool
def wolfram_alpha_query(query: str) -> str:
    """
    Perform mathematical calculations, scientific computations, and get factual data using Wolfram Alpha.
    Args:
        query: The query to send to Wolfram Alpha (e.g., 'solve x^2 + 2x + 1 = 0', 'population of Tokyo', 'derivative of sin(x)')
    Returns:
        The result from Wolfram Alpha as a string
    """
    url = "http://api.wolframalpha.com/v2/query"
    params = {"input": query, "appid": WOLFRAM_APP_ID, "output": "XML"}
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
def web_search_tool(query: str, max_results: int = 5) -> list:
    """
    Perform a web search using Tavily and return the results.

    Args:
        query: The search query to perform.
        max_results: The maximum number of results to return.

    Returns:
        A list of search results.
    """
    try:
        response = tavily_client.search(query, max_results=max_results)
        return response['results']
    except Exception as e:
        return [{"error": str(e)}]