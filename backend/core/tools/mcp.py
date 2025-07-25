from agents.mcp import MCPServerStdio
import os
from pathlib import Path
import dotenv


PROJECT_ROOT = Path(__file__).parent.parent

env_path = PROJECT_ROOT / ".env"
try:
    if env_path.exists():
        dotenv.load_dotenv(env_path)
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

alpha_vantage_mcp_server = MCPServerStdio(
    params={
        "command": "python",
        "args": ["-m", "src.alpha_vantage_mcp.server"],
        "cwd": str(PROJECT_ROOT / "backend/alpha-vantage-mcp"),
        "env": os.environ.copy(),
    }
)
