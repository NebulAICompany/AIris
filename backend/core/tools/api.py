import requests
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from backend.shared.constants import tavily_client, WOLFRAM_APP_ID
from datetime import datetime
from zoneinfo import ZoneInfo


@tool(parse_docstring=True)
async def time_now(tz: str = "Europe/Istanbul") -> str:
    """Get the current date and time in ISO 8601 format for a specified timezone.

    Args:
        tz: IANA timezone identifier (for example, 'Europe/Istanbul', 'America/New_York', 'UTC').
            Defaults to 'Europe/Istanbul' if not specified.
    """
    return datetime.now(ZoneInfo(tz)).isoformat()


@tool(parse_docstring=True)
def wolfram_alpha_query(query: str) -> str:
    """Perform mathematical calculations, scientific computations, and get factual data using Wolfram Alpha.

    Args:
        query: The query to send to Wolfram Alpha (for example, 'solve x^2 + 2x + 1 = 0', 'population of Tokyo', 'derivative of sin(x)').
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


@tool(parse_docstring=True)
def web_search_tool(query: str, max_results: int = 5) -> list:
    """Perform a web search using Tavily and return the results.

    Args:
        query: The search query to perform.
        max_results: The maximum number of results to return. (default 5, max 10)
    """
    try:
        response = tavily_client.search(
            query, max_results=max_results, auto_parameters=True
        )
        return response["results"]
    except Exception as e:
        return [{"error": str(e)}]


@tool(parse_docstring=True)
def get_uploaded_files_count() -> str:
    """Get the total count of files uploaded to the system.
    """
    try:
        from backend.utils.uploads_database import uploads_db

        total_count = uploads_db.count_uploads()
        count_by_type = uploads_db.count_by_file_type()

        result = f"Total uploaded files: {total_count}\n"

        if count_by_type:
            result += "\nBreakdown by file type:\n"
            for file_type, count in count_by_type.items():
                result += f"  {file_type}: {count} files\n"

        return result
    except Exception as e:
        return f"Error retrieving upload count: {str(e)}"


@tool(parse_docstring=True)
def list_uploaded_files(limit: int = 10) -> str:
    """List recently uploaded files with their details.

    Args:
        limit: Maximum number of files to return (default 10, max 100)
    """
    try:
        from backend.utils.uploads_database import uploads_db

        # Ensure limit is within reasonable bounds
        limit = min(max(1, limit), 100)

        uploads = uploads_db.get_all_uploads(limit=limit)

        if not uploads:
            return "No files have been uploaded yet."

        result = f"Recently uploaded files (showing {len(uploads)} most recent):\n\n"

        for upload in uploads:
            result += f"📄 {upload['file_name']}\n"
            result += f"   Type: {upload['file_type']}\n"
            result += f"   Uploaded: {upload['upload_date']}\n\n"

        return result
    except Exception as e:
        return f"Error retrieving uploaded files: {str(e)}"
