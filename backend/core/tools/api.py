import requests
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from backend.shared.constants import tavily_client, WOLFRAM_APP_ID


@tool(parse_docstring=True, response_format="content_and_artifact")
def wolfram_alpha_query(query: str):
    """Perform mathematical calculations, scientific computations, and get factual data using Wolfram Alpha.

    Args:
        query: The query to send to Wolfram Alpha (e.g., 'solve x^2 + 2x + 1 = 0', 'population of Tokyo', 'derivative of sin(x)')
    """
    url = "http://api.wolframalpha.com/v2/query"
    params = {"input": query, "appid": WOLFRAM_APP_ID, "output": "XML"}
    try:
        response = requests.get(url, params=params)

        if response.status_code != 200:
            error_msg = f"Error: HTTP {response.status_code}"
            return error_msg, {"name": "Wolfram Alpha", "description": "API error"}

        # Parse XML response
        root = ET.fromstring(response.text)

        # Check if query was successful
        if root.get("success") != "true":
            error_msg = "Error: Query was not successful"
            return error_msg, {"name": "Wolfram Alpha", "description": "Query failed"}

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
                        content = plaintext.text
                        artifact = {
                            "name": "Wolfram Alpha",
                            "description": f"Mathematical computation: {query[:50]}...",
                        }
                        return content, artifact

        # If no specific result pod found, return first available text
        for pod in pods:
            subpods = pod.findall("subpod")
            for subpod in subpods:
                plaintext = subpod.find("plaintext")
                if plaintext is not None and plaintext.text:
                    content = plaintext.text
                    artifact = {
                        "name": "Wolfram Alpha",
                        "description": f"Query: {query[:50]}...",
                    }
                    return content, artifact

        no_results = "No results found"
        return no_results, {"name": "Wolfram Alpha", "description": "No results"}

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        return error_msg, {"name": "Wolfram Alpha", "description": "Exception occurred"}


@tool(parse_docstring=True, response_format="content_and_artifact")
def web_search_tool(query: str, search_depth: str = "basic"):
    """Perform a web search using Tavily and return the results.

    Args:
        query: The search query to perform.
        search_depth: The depth of the search (basic, advanced). Defaults to "basic".
    """
    try:
        response = tavily_client.search(
            query,
            max_results=10,
            auto_parameters=True,
            search_depth=search_depth,
            # topic="finance", Kaldırdım şu anlık, bazı sıkıntıları var gibi duruyor.
        )
        if not response:
            return "No search results available.", []

        # Build content text for LLM (without URLs)
        content_parts = []
        sources = []

        results = response.get("results", [])

        for r in results:
            title = r.get("title", "No title")
            content = r.get("content", "")
            url = r.get("url", "")

            content_parts.append(f"Title: {title}\nContent: {content}\n")

            if url:
                sources.append({"name": title, "url": url})

        # Return content for LLM and artifact for system
        content = "\n".join(content_parts)
        artifact = sources

        return content, artifact
    except Exception as e:
        return f"Error searching web: {str(e)}"


@tool(parse_docstring=True)
def get_uploaded_files_count() -> str:
    """Get the total count of files uploaded to the system."""
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
