from agents.mcp import MCPServerStdio
import os
from backend.shared.constants import PROJECT_ROOT
import dotenv
from backend.shared.logger import get_logger

logger = get_logger("MCP_TOOLS")


env_path = PROJECT_ROOT / ".env"

try:
    if env_path.exists():
        dotenv.load_dotenv(env_path)
except Exception as e:
    logger.warning(f"Warning: Could not load .env file: {e}")

alpha_vantage_mcp_server = MCPServerStdio(
    params={
        "command": "python",
        "args": ["-m", "src.alpha_vantage_mcp.server"],
        "cwd": str(PROJECT_ROOT / "backend/server/alpha-vantage-mcp"),
        "env": os.environ.copy(),
    }
)

mcp_servers = [
    alpha_vantage_mcp_server,
]