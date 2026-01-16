from e2b_code_interpreter import Sandbox
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv
import uuid
from datetime import datetime
from backend.shared.constants import CHARTS_DIR
import json

load_dotenv()

# Chart data management functions (similar to finance.py)
CHART_DATA_FILE = CHARTS_DIR / "chart_data.json"


def set_chart_data(data):
    """Set chart data to JSON file storage - overwrites file each time"""
    try:
        # Ensure CHARTS_DIR exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        # Overwrite file with new chart data (don't append)
        with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([data], f, ensure_ascii=False, indent=2)

    except Exception as e:
        pass


class CodeInterpreterInput(BaseModel):
    code: str = Field(description="Python code to execute")


@tool(
    args_schema=CodeInterpreterInput,
)
def execute_code_and_save_image(code: str) -> dict:
    """
    Execute Python code in a sandboxed environment and save generated chart images.

    Args:
        code: Python code to execute, typically matplotlib plotting code that generates visualizations.

    Returns:
        dict: Execution result containing the output of the code execution and chart metadata.
    """
    sandbox = None
    try:
        # Create sandbox and execute code
        sandbox = Sandbox.create(timeout=30)
        execution = sandbox.run_code(code)

        if not execution.results:
            return {"error": "No results from code execution"}

        first_result = execution.results[0]

        # Check if PNG was generated
        if first_result.png:
            # Generate unique chart ID
            chart_id = f"chart_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Get base64 PNG data (already base64 encoded from sandbox)
            png_base64 = first_result.png

            # Create HTML wrapper with embedded PNG
            chart_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: white;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <img src="data:image/png;base64,{png_base64}" alt="Chart" />
</body>
</html>
"""

            # Save HTML file
            chart_file = CHARTS_DIR / f"{chart_id}.html"
            CHARTS_DIR.mkdir(parents=True, exist_ok=True)

            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(chart_html)

            # Create chart metadata
            chart_data = {
                "filename": f"{chart_id}.html",
                "data": chart_html,
                "reference": chart_id,
                "type": "text/html",
                "chart_type": "custom_plot",
                "created_at": datetime.now().isoformat(),
                "file_path": str(chart_file),
            }

            # Save chart data
            set_chart_data(chart_data)

            return "chart created successfully"
    except Exception as e:
        return f"Error executing code: {str(e)}"
    finally:
        if sandbox:
            try:
                sandbox.kill()
            except:
                pass
