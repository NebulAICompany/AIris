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
    name="Alpha Vantage MCP Server",
    params={
        "command": "python",
        "args": ["-m", "src.alpha_vantage_mcp.server"],
        "cwd": str(PROJECT_ROOT / "backend/server/alpha-vantage-mcp"),
        "env": os.environ.copy(),
    }
)

all_mcp_servers = [
    alpha_vantage_mcp_server,
    #Add other MCP servers here as needed
]

# ! MCP Server Connection Management
_servers_connected = False

async def connect_mcp_servers():
    """Connect all MCP servers"""
    global _servers_connected
    if not _servers_connected:
        try:
            for server in all_mcp_servers:
                await server.connect()
                logger.info(f"MCP server {server.name} is connected")
            _servers_connected = True
            logger.info("All MCP servers connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect MCP servers: {e}")
            raise

async def disconnect_mcp_servers():
    """Disconnect all MCP servers"""
    global _servers_connected
    if _servers_connected:
        try:
            for server in all_mcp_servers:
                if hasattr(server, '_session'):
                    await server.cleanup()
                logger.info(f"MCP server {server.name} is disconnected")
            _servers_connected = False
            logger.info("All MCP servers disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect MCP servers: {e}")
