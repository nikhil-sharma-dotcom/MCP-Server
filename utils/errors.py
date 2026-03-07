

from utils.mcp_errors import MCPToolError

import logging

logger = logging.getLogger(__name__)

def raise_tool_error(tool: str, error: Exception):
    logger.error(f"{tool} failed: {error}")
    raise MCPToolError(str(error), tool)
