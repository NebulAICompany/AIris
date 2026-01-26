from e2b_code_interpreter import Sandbox
from langchain.tools import tool
from dotenv import load_dotenv
import uuid
from datetime import datetime
from backend.shared.constants import POWERPOINT_DIR
from backend.shared.logger import get_logger

load_dotenv()

logger = get_logger("POWERPOINT_TOOLS")


@tool(parse_docstring=True, return_direct=True)
def create_powerpoint_from_code(code: str) -> str:
    """Create PowerPoint presentations by executing Python code in a sandboxed environment.

    Use this tool for creating PowerPoint presentations with python-pptx library.
    The code should create a Presentation object, add slides, and save the file.

    Args:
        code: Complete Python code that creates and saves a PowerPoint presentation.
            The code must include all required imports (from pptx import Presentation)
            and save the presentation to a file named 'output.pptx' (e.g., prs.save('output.pptx')).
            The saved file will be automatically moved to the documents directory.
    """
    sandbox = None
    try:
        # Generate unique filename for output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        output_filename = f"presentation_{timestamp}_{unique_id}.pptx"
        output_path = POWERPOINT_DIR / output_filename

        # Create sandbox and execute code
        sandbox = Sandbox.create(timeout=60)

        try:
            sandbox.commands.run("pip install python-pptx")
        except Exception as e:
            return f"Failed to install python-pptx: {str(e)}"

        # Execute the user's code
        execution = sandbox.run_code(code)

        # Check for execution errors
        if execution.error:
            return f"Code execution error: {execution.error.value}"

        # Download the PPTX file from sandbox
        try:
            pptx_content = sandbox.files.read("/home/user/output.pptx", format="bytes")
            logger.info(f"PPTX content: {pptx_content}")

            with open(output_path, "wb") as f:
                f.write(pptx_content)

            return f"PowerPoint presentation created successfully: {output_filename}"
        except Exception as e:
            return f"Failed to save PowerPoint file: {str(e)}"

    except Exception as e:
        return f"Error executing code: {str(e)}"
    finally:
        if sandbox:
            try:
                sandbox.kill()
            except Exception as e:
                print(f"Warning: Failed to kill sandbox: {str(e)}")
